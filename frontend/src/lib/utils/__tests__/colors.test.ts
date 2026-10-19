/**
 * colors.test.ts — `hexToHsl()`, the exact inverse of `hslToHex()` (`$lib/utils/colors`).
 *
 * Why the round trip matters: a caller that moves a colour in HSL — a lightness step, a hue rotation — and writes it
 * back must get the colour it started from when it moves nothing. That holds only if hex → HSL → hex is lossless
 * (within one unit per channel, the rounding of `hslToHex`) and if a malformed colour degrades to `null`, a branch the
 * caller can handle, rather than to black — a black slice is an invisible bug.
 *
 * **The colours it is proven on are the ones the charts draw today**: the category colours of the designer's round 3,
 * her final palette on the rule of her round 2 (GR1, D-T17) — every asset-type family, every sector and the engine's
 * two buckets, in both themes — read through `categoryColor` (`$lib/theme/chartCategories`), the charts' one read
 * point. So an edit of the designer's tables is measured here.
 *
 * Until round 2 the allocation charts derived a family's shades in HSL from hand-written 14-slot palettes, and this file
 * measured those palettes. The shades are now OKLab mixes (`$lib/theme/chartShades`) and the palettes are gone, so
 * `hexToHsl` has no production caller left; `hslToHex` draws the measure tool's lines (`MeasurePanel.svelte`). What the
 * category tables must be — their slots, no repeat, how far apart — is `src/__tests__/palettes.test.ts`'s and
 * `src/lib/theme/chartCategories.test.ts`'s, not repeated here.
 *
 * No runes, no DOM: this stays in the default `node` environment.
 *
 * @module utils/__tests__/colors.test
 */
import {describe, expect, it} from 'vitest';

import {CATEGORY_BUCKETS, CATEGORY_KEYS, categoryColor, type CategoryKind} from '$lib/theme/chartCategories';

import {hexToHsl, hslToHex} from '../colors';

// =============================================================================
// The colours under test — the category colours, read as the charts read them
// =============================================================================

const KINDS: readonly CategoryKind[] = ['type', 'sector'];

/** Each table in each theme, its keys and the two buckets beside it, read through `categoryColor`. */
const TABLES: ReadonlyArray<readonly [string, readonly string[]]> = KINDS.flatMap((kind) => [false, true].map((dark) => [`${kind} ${dark ? 'dark' : 'light'}`, [...CATEGORY_KEYS[kind], ...CATEGORY_BUCKETS].map((key) => categoryColor(kind, key, dark))] as const));

/** Split a `#rrggbb` (or bare `rrggbb`) into its three 0-255 channels. */
function channels(hex: string): [number, number, number] {
    const raw = hex.replace(/^#/, '');
    return [parseInt(raw.slice(0, 2), 16), parseInt(raw.slice(2, 4), 16), parseInt(raw.slice(4, 6), 16)];
}

// =============================================================================
// The colours under test — checked first, so no loop below can pass on nothing
// =============================================================================

describe('the colours under test', () => {
    it('are the category tables of both kinds, in both themes, the keys certainly there among them', () => {
        expect(TABLES.map(([name]) => name)).toEqual(['type light', 'type dark', 'sector light', 'sector dark']);
        expect(CATEGORY_KEYS.type, 'barrier: the type table').toEqual(expect.arrayContaining(['STOCK', 'ETF', 'OTHER']));
        expect(CATEGORY_KEYS.sector, 'barrier: the sector table').toEqual(expect.arrayContaining(['Technology', 'Health Care', 'Other']));
    });

    it.each(TABLES)('%s: every colour is a #rrggbb, the notation hexToHsl reads', (_name, colours) => {
        expect(colours.length, 'barrier: the table has colours').toBeGreaterThan(CATEGORY_BUCKETS.length);
        expect(colours.filter((colour) => !/^#[0-9a-f]{6}$/i.test(colour))).toEqual([]);
    });
});

// =============================================================================
// Round trip — the property the whole HSL conversion rests on
// =============================================================================

describe('hexToHsl — round trip through hslToHex', () => {
    it.each(TABLES)('reproduces every colour of the %s table within ±1 per channel', (_name, palette) => {
        // Positive barrier first: an empty palette would make the loop below
        // pass by doing nothing at all.
        expect(palette.length).toBeGreaterThan(0);

        for (const hex of palette) {
            const hsl = hexToHsl(hex);
            expect(hsl, `hexToHsl(${hex}) must parse`).not.toBeNull();

            const back = hslToHex(hsl!.h, hsl!.s, hsl!.l);
            const [r0, g0, b0] = channels(hex);
            const [r1, g1, b1] = channels(back);

            expect(Math.abs(r1 - r0), `${hex} → ${back} red`).toBeLessThanOrEqual(1);
            expect(Math.abs(g1 - g0), `${hex} → ${back} green`).toBeLessThanOrEqual(1);
            expect(Math.abs(b1 - b0), `${hex} → ${back} blue`).toBeLessThanOrEqual(1);
        }
    });

    it.each(TABLES)('keeps h in 0-360 and s/l in 0-100 for every colour of the %s table', (_name, palette) => {
        expect(palette.length).toBeGreaterThan(0);

        for (const hex of palette) {
            const hsl = hexToHsl(hex);
            expect(hsl, `hexToHsl(${hex}) must parse`).not.toBeNull();

            expect(hsl!.h, `${hex} hue`).toBeGreaterThanOrEqual(0);
            expect(hsl!.h, `${hex} hue`).toBeLessThanOrEqual(360);
            expect(hsl!.s, `${hex} saturation`).toBeGreaterThanOrEqual(0);
            expect(hsl!.s, `${hex} saturation`).toBeLessThanOrEqual(100);
            expect(hsl!.l, `${hex} lightness`).toBeGreaterThanOrEqual(0);
            expect(hsl!.l, `${hex} lightness`).toBeLessThanOrEqual(100);
            expect(Number.isNaN(hsl!.h) || Number.isNaN(hsl!.s) || Number.isNaN(hsl!.l), `${hex} produced NaN`).toBe(false);
        }
    });
});

// =============================================================================
// Accepted input forms
// =============================================================================

describe('hexToHsl — accepted notations', () => {
    it('reads the 3-digit form as the doubled 6-digit form', () => {
        const short = hexToHsl('#abc');
        const long = hexToHsl('#aabbcc');

        expect(short).not.toBeNull();
        expect(long).not.toBeNull();
        expect(short).toEqual(long);
        // Pin the actual value too, so `toEqual` cannot pass by both sides
        // degrading to the same wrong answer.
        expect(long!.h).toBeCloseTo(210, 6);
        expect(long!.s).toBeCloseTo(25, 6);
        expect(long!.l).toBeCloseTo(73.333333, 4);
    });

    it('accepts both forms without the leading #', () => {
        expect(hexToHsl('aabbcc')).toEqual(hexToHsl('#aabbcc'));
        expect(hexToHsl('abc')).toEqual(hexToHsl('#abc'));
        expect(hexToHsl('abc')).toEqual(hexToHsl('#aabbcc'));
        // …and that shared value is a real parse, not four `null`s agreeing.
        expect(hexToHsl('aabbcc')).not.toBeNull();
    });

    it('is case-insensitive and tolerates surrounding whitespace', () => {
        const canonical = hexToHsl('#0d9488');
        expect(canonical).not.toBeNull();
        expect(hexToHsl('#0D9488')).toEqual(canonical);
        expect(hexToHsl('  #0d9488  ')).toEqual(canonical);
    });

    it.each(TABLES)('accepts every colour of the %s table with and without the #', (_name, palette) => {
        expect(palette.length).toBeGreaterThan(0);
        for (const hex of palette) {
            const withHash = hexToHsl(hex);
            expect(withHash, `hexToHsl(${hex})`).not.toBeNull();
            expect(hexToHsl(hex.slice(1))).toEqual(withHash);
        }
    });
});

// =============================================================================
// Exactness — the values are unrounded, and the inverse is the real inverse
// =============================================================================

describe('hexToHsl — exact values', () => {
    it('places the primaries on their canonical hues', () => {
        expect(hexToHsl('#ff0000')).toEqual({h: 0, s: 100, l: 50});
        expect(hexToHsl('#00ff00')).toEqual({h: 120, s: 100, l: 50});
        expect(hexToHsl('#0000ff')).toEqual({h: 240, s: 100, l: 50});
    });

    it('wraps a negative intermediate hue into 0-360 (magenta = 300°)', () => {
        // max === red with blue > green drives the `h < 0 → h += 360` branch.
        const hsl = hexToHsl('#ff00ff');
        expect(hsl).not.toBeNull();
        expect(hsl!.h).toBeCloseTo(300, 6);
        expect(hsl!.h).toBeGreaterThanOrEqual(0);
    });

    it('returns unrounded components', () => {
        const hsl = hexToHsl('#0d9488');
        expect(hsl).not.toBeNull();
        expect(hsl!.h).toBeCloseTo(174.666666, 4);
        expect(hsl!.s).toBeCloseTo(83.850931, 4);
        expect(hsl!.l).toBeCloseTo(31.568627, 4);
        // The point of the bullet: these are NOT snapped to integers. Rounding
        // here would quantise every derived shade by up to half a step.
        expect(hsl!.l).not.toBe(Math.round(hsl!.l));
        expect(hsl!.s).not.toBe(Math.round(hsl!.s));
    });
});

// =============================================================================
// Achromatic — the branch where the saturation formula would divide by zero
// =============================================================================

describe('hexToHsl — achromatic inputs', () => {
    it.each([
        ['#000000', 0],
        ['#ffffff', 100],
        ['#a3a3a3', 63.921568],
    ] as const)('gives %s zero saturation and no NaN', (hex, expectedL) => {
        const hsl = hexToHsl(hex);
        expect(hsl, `hexToHsl(${hex}) must parse`).not.toBeNull();

        expect(hsl!.s).toBe(0);
        expect(hsl!.h).toBe(0);
        expect(hsl!.l).toBeCloseTo(expectedL, 4);

        expect(Number.isNaN(hsl!.h)).toBe(false);
        expect(Number.isNaN(hsl!.s)).toBe(false);
        expect(Number.isNaN(hsl!.l)).toBe(false);
        expect(Number.isFinite(hsl!.s)).toBe(true);
        expect(Number.isFinite(hsl!.l)).toBe(true);
    });

    it('round-trips the extremes back to the same hex', () => {
        for (const hex of ['#000000', '#ffffff', '#a3a3a3']) {
            const hsl = hexToHsl(hex)!;
            expect(hslToHex(hsl.h, hsl.s, hsl.l)).toBe(hex);
        }
    });
});

// =============================================================================
// Rejection — null, never black, never a throw
// =============================================================================

describe('hexToHsl — malformed input', () => {
    it.each([
        ['empty string', ''],
        ['a word', 'nope'],
        ['five digits', '#12345'],
        ['non-hex letters', '#gggggg'],
        ['a CSS rgb() function', 'rgb(1,2,3)'],
    ])('returns null for %s', (_label, input) => {
        expect(hexToHsl(input)).toBeNull();
    });

    it('does not throw, and never degrades to black', () => {
        for (const input of ['', 'nope', '#12345', '#gggggg', 'rgb(1,2,3)', '#', '#1234567', 'hsl(0,0%,0%)']) {
            let result: ReturnType<typeof hexToHsl>;
            expect(
                () => {
                    result = hexToHsl(input);
                },
                `hexToHsl(${JSON.stringify(input)}) threw`,
            ).not.toThrow();

            // `null` and "black" are different answers; conflating them is what
            // turns a typo into an invisible slice.
            expect(result!, `hexToHsl(${JSON.stringify(input)})`).toBeNull();
            expect(result!).not.toEqual({h: 0, s: 0, l: 0});
        }
    });

    it('still parses valid input in the same batch, so the rejections mean something', () => {
        // Guards the suite above against a hypothetical `hexToHsl = () => null`,
        // which would make every rejection test pass.
        expect(hexToHsl('#1a4031')).not.toBeNull();
        expect(hexToHsl('#4ade80')).not.toBeNull();
    });
});
