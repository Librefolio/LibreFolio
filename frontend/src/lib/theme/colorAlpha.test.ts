/**
 * colorAlpha — pure unit tests (node env, no jsdom).
 *
 * `$lib/theme/colorAlpha` is where the charts' alpha helpers moved in colour workstream R (wave W0, R-4), a wave whose
 * rule is «same pixels». These tests hold the module to that rule, and to the one thing the move was allowed to change.
 *
 * - **The same strings on the inputs the charts pass today.** `toRgba` replaced `hexToRgba` (`lineChartHelpers.ts`),
 *   and its oracle is the old helper itself, kept verbatim below as `legacyHexToRgba`: on every `#rrggbb` of the chart
 *   palettes, in any letter case, and at every alpha the charts compute, the two outputs must match character for
 *   character — `rgba(r,g,b,a)` with no spaces, the alpha printed as JavaScript prints it. `withHexAlpha` replaced
 *   `color + '88'` / `color + '44'`, and its oracle is that concatenation. `withAlpha` moved verbatim from
 *   `lotChartShared.ts`; its tests moved with it, every expectation unchanged.
 * - **What changed is what they accept.** The old helpers assumed a `#rrggbb`. On anything else `hexToRgba` wrote a
 *   `NaN` into the colour — `#abc` became `rgba(171,12,NaN,a)` — and `'#abc' + '88'` made an invalid `#abc88`: strings
 *   the canvas ignores, so a series silently lost its fill. Now a colour gets its alpha in a notation that can carry
 *   it, or comes back unchanged — never with a `NaN` in it.
 * - **`parseRgba` reads the alpha a colour already carries** (DV, T's review of the bridge): the opacity of a
 *   `#rrggbbaa` or `#rgba`, the fourth number of `rgba()`/`hsla()` or the one after `/`, a percentage read as such,
 *   clamped to 0–1; 1 for an opaque notation. The channels are `parseRgb`'s, and so are the notations it refuses: it
 *   reads, it never guesses — an alpha it cannot read makes the colour unreadable, never opaque. `./contrast`
 *   composites a translucent colour with it before measuring.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */
import {describe, expect, it} from 'vitest';
import {parseRgb, parseRgba, toRgba, withAlpha, withHexAlpha} from '$lib/theme/colorAlpha';

/**
 * `hexToRgba` exactly as `lineChartHelpers.ts` defined it before R-4: the oracle of the golden tests. It is copied
 * here rather than imported so that the reference cannot move together with the code under test.
 */
function legacyHexToRgba(hex: string, alpha: number): string {
    const h = hex.replace('#', '');
    const r = parseInt(h.substring(0, 2), 16);
    const g = parseInt(h.substring(2, 4), 16);
    const b = parseInt(h.substring(4, 6), 16);
    return `rgba(${r},${g},${b},${alpha})`;
}

/**
 * Six-digit hexes the charts really draw with: the line and candlestick colours (`COLORS` of `lineChartHelpers.ts`),
 * the default signal colours (`DEFAULT_SIGNAL_COLORS`), GrowthChart's stacked areas, the fixtures of the chart tests,
 * and the two ends of every channel.
 */
const PALETTE = ['#1a4031', '#4ade80', '#16a34a', '#ef4444', '#f87171', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#60a5fa', '#9caf9c', '#6b8e6b', '#10b981', '#34d399', '#112233', '#3355ff', '#000000', '#ffffff'];

/** The same colours as a hand-written hex may spell them: lower, upper and mixed case. */
const HEXES = [...PALETTE, ...PALETTE.map((hex) => hex.toUpperCase()), '#Ef4444', '#3b82F6'];

/**
 * Alphas as the charts compute them — products and fades included (stale-opacity fades, band and region fills, the
 * candlestick volume bars). The old helper printed whatever number it was handed, so the golden has to prove the new
 * one does too: no rounding, no fixed decimals.
 */
const ALPHAS = [1, 0.55, 0.15 * 0.8, 0.12 * 0.8, 0.18 * 0.8, 0.12, 0.2, 0.06, 0.08, 0.575, (0.575 + 0.15) / 2, 1 - (3.5 / 14) * 0.85, 0.1 * 0.575, 0.02, 0];

/** An `rgba(r,g,b,a)` as the helper writes it: no spaces, integer channels within 0–255, the alpha it was given. */
function isWellFormedRgba(color: string, alpha: number): boolean {
    const match = /^rgba\((\d+),(\d+),(\d+),([^,()]+)\)$/.exec(color);
    return match !== null && [match[1], match[2], match[3]].every((channel) => Number(channel) <= 255) && match[4] === String(alpha);
}

describe('toRgba', () => {
    describe('golden: on a #rrggbb, the string the old hexToRgba drew', () => {
        it('the oracle is the old helper (pinned by hand, so the comparison below is about something)', () => {
            expect(legacyHexToRgba('#1a4031', 0.5)).toBe('rgba(26,64,49,0.5)');
            expect(legacyHexToRgba('#EF4444', 0.15 * 0.8)).toBe(`rgba(239,68,68,${0.15 * 0.8})`);
        });

        it('matches it character for character on every palette hex, in any letter case, at every alpha the charts compute', () => {
            const cases = HEXES.flatMap((hex) => ALPHAS.map((alpha) => ({hex, alpha})));
            expect(cases, 'positive control: the golden compares something').not.toHaveLength(0);

            // One diff names every colour/alpha pair whose string moved.
            const moved = cases.filter(({hex, alpha}) => toRgba(hex, alpha) !== legacyHexToRgba(hex, alpha)).map(({hex, alpha}) => `${hex} @ ${alpha}: ${toRgba(hex, alpha)} — was ${legacyHexToRgba(hex, alpha)}`);
            expect(moved).toEqual([]);
        });

        it('a #rrggbbaa keeps its first six digits and takes the new alpha, as the old helper read it', () => {
            for (const hex of ['#16a34a80', '#1a4031ff', '#EF444400']) {
                for (const alpha of [1, 0.55, 0]) expect(toRgba(hex, alpha), `${hex} @ ${alpha}`).toBe(legacyHexToRgba(hex, alpha));
            }
            expect(toRgba('#16a34a80', 0.55)).toBe('rgba(22,163,74,0.55)');
        });
    });

    describe('the other notations get the alpha too', () => {
        it('#rgb and #rgba are expanded digit by digit — where the old helper read #abc as ab|c|"" and wrote a NaN', () => {
            expect(toRgba('#abc', 0.5)).toBe('rgba(170,187,204,0.5)');
            expect(toRgba('#ABC', 0.5)).toBe('rgba(170,187,204,0.5)');
            // The fourth digit is an alpha: replaced, like the last two of a #rrggbbaa.
            expect(toRgba('#abcd', 0.5)).toBe('rgba(170,187,204,0.5)');
            expect(toRgba('#0f0', 0.25)).toBe('rgba(0,255,0,0.25)');

            // Contrast: what the old helper drew for the same colour.
            expect(legacyHexToRgba('#abc', 0.5)).toBe('rgba(171,12,NaN,0.5)');
        });

        it('rgb() and rgba(), comma or space syntax, % channels: an rgba() with the alpha replaced', () => {
            expect(toRgba('rgb(22, 163, 74)', 0.5)).toBe('rgba(22,163,74,0.5)');
            expect(toRgba('rgb(22 163 74)', 0.5)).toBe('rgba(22,163,74,0.5)');
            expect(toRgba('rgb(22 163 74 / 0.3)', 0.5)).toBe('rgba(22,163,74,0.5)');
            expect(toRgba('rgba(22, 163, 74, 0.3)', 0.5)).toBe('rgba(22,163,74,0.5)');
            expect(toRgba('RGBA(22,163,74,.3)', 0.5)).toBe('rgba(22,163,74,0.5)');
            // 50% of 255 is 127.5: the channel is rounded, never written as a fraction.
            expect(toRgba('rgb(100%, 50%, 0%)', 0.5)).toBe('rgba(255,128,0,0.5)');
            expect(toRgba('rgb(22.4, 163.6, 74)', 0.5)).toBe('rgba(22,164,74,0.5)');
        });

        it('hsl() and hsla() are converted to rgba(), channels rounded', () => {
            expect(toRgba('hsl(120, 50%, 50%)', 0.5)).toBe('rgba(64,191,64,0.5)');
            expect(toRgba('hsl(120 50% 50%)', 0.5)).toBe('rgba(64,191,64,0.5)');
            expect(toRgba('hsla(120, 50%, 50%, 0.3)', 0.5)).toBe('rgba(64,191,64,0.5)');
            expect(toRgba('hsl(120deg 50% 50% / 0.3)', 0.5)).toBe('rgba(64,191,64,0.5)');
            expect(toRgba('hsl(0, 100%, 50%)', 1)).toBe('rgba(255,0,0,1)');
            expect(toRgba('hsl(0, 0%, 100%)', 1)).toBe('rgba(255,255,255,1)');
            // The lot charts' own shape: hsl(210 68% 44%) is rgb(35.9, 112.2, 188.5).
            expect(toRgba('hsl(210 68% 44%)', 0.5)).toBe('rgba(36,112,188,0.5)');
        });

        it('oklch() keeps its own notation with the alpha after a slash — converting it to sRGB would change the colour', () => {
            expect(toRgba('oklch(0.62 0.19 145)', 0.5)).toBe('oklch(0.62 0.19 145 / 0.5)');
            expect(toRgba('oklch(62% 0.19 145 / 0.8)', 0.5)).toBe('oklch(62% 0.19 145 / 0.5)');
            expect(toRgba('OKLCH(0.62 0.19 145)', 0.5)).toBe('oklch(0.62 0.19 145 / 0.5)');
        });

        it('a colour it cannot put an alpha into comes back unchanged: named colours, var(), color-mix()', () => {
            for (const color of ['red', 'transparent', 'currentColor', 'var(--lf-green)', 'color-mix(in srgb, #16a34a 50%, white)']) {
                expect(toRgba(color, 0.5), color).toBe(color);
            }
        });
    });

    describe('never a NaN', () => {
        /** Colours the old helper turned into an rgba() with a NaN in it: short or broken hexes, other notations, names. */
        const LEGACY_NAN = ['#abc', '#1', '', '#ggg', 'red', 'rgb(22, 163, 74)', 'hsl(120, 50%, 50%)', 'var(--lf-green)'];

        /** Malformed hexes, functional notations with missing or non-numeric channels, and things that are no colour at all. */
        const MALFORMED = [
            '#',
            '#12',
            '#12345',
            '#1234567',
            '#123456789',
            '#gggggg',
            '#12345g',
            'rgb()',
            'rgb(1, 2)',
            'rgb(a, b, c)',
            'rgba(1, 2, x, 0.5)',
            'rgb(1, 2, 3',
            'rgb(Infinity, 0, 0)',
            'hsl()',
            'hsl(120, 50%)',
            'hsl(x, y, z)',
            'hsla(120, 50%, abc, 1)',
            'hsl(1e999, 50%, 50%)',
            'oklch()',
            'oklch(0.5 0.1)',
            'not a colour',
            'url(#gradient)',
        ];

        it('control: the probe catches the failure it guards against — the old helper wrote a NaN on these', () => {
            // A NaN check that never fires cannot be told apart from one that cannot fire.
            for (const color of LEGACY_NAN) expect(legacyHexToRgba(color, 0.5), JSON.stringify(color)).toContain('NaN');
        });

        it('the same inputs, and every malformed one, give no NaN now: the colour comes back unchanged, or as a well-formed rgba()', () => {
            const broken = [...LEGACY_NAN, ...MALFORMED].flatMap((color) => {
                const out = toRgba(color, 0.5);
                return out.includes('NaN') || !(out === color || isWellFormedRgba(out, 0.5)) ? [`${JSON.stringify(color)} → ${out}`] : [];
            });
            expect(broken).toEqual([]);
        });
    });
});

// Moved verbatim from lotChartShared.test.ts together with the helper (R-4): the lot charts' contract, unchanged.
describe('withAlpha', () => {
    it('rewrites an hsl() color into hsla() with the alpha inserted literally', () => {
        expect(withAlpha('hsl(210 68% 44%)', 0.5)).toBe('hsla(210 68% 44%, 0.5)');
    });

    it('appends a clamped alpha byte to a #rrggbb color', () => {
        expect(withAlpha('#00ff00', 1)).toBe('#00ff00ff');
        expect(withAlpha('#00ff00', 0)).toBe('#00ff0000');
        // 0.5 * 255 = 127.5 → rounds to 128 → 0x80
        expect(withAlpha('#112233', 0.5)).toBe('#11223380');
    });

    it('clamps an out-of-range alpha before scaling the hex byte', () => {
        expect(withAlpha('#112233', 2)).toBe('#112233ff');
        expect(withAlpha('#112233', -1)).toBe('#11223300');
    });

    it('pads a small alpha byte to two hex digits', () => {
        // 0.02 * 255 = 5.1 → 5 → "05", not "5"
        expect(withAlpha('#112233', 0.02)).toBe('#11223305');
    });

    it('returns unrecognised color shapes unchanged', () => {
        expect(withAlpha('red', 0.5)).toBe('red');
        expect(withAlpha('#abc', 0.5)).toBe('#abc');
        expect(withAlpha('rgba(1,2,3,0.4)', 0.5)).toBe('rgba(1,2,3,0.4)');
    });
});

describe('withHexAlpha', () => {
    it('on a #rrggbb: the two digits appended, exactly the string color + alphaHex made', () => {
        expect(withHexAlpha('#3b82f6', '44')).toBe('#3b82f644');
        expect(withHexAlpha('#1A4031', '88')).toBe('#1A403188');

        // The oracle is the concatenation it replaced, over every palette hex and letter case.
        const moved = HEXES.flatMap((hex) => ['88', '44', '00', 'ff'].filter((alphaHex) => withHexAlpha(hex, alphaHex) !== hex + alphaHex).map((alphaHex) => `${hex} + ${alphaHex}: ${withHexAlpha(hex, alphaHex)}`));
        expect(moved).toEqual([]);
    });

    it('on any other colour: the same opacity through toRgba — 0x88 / 255 — never a concatenation', () => {
        expect(withHexAlpha('#abc', '88')).toBe(`rgba(170,187,204,${0x88 / 255})`);
        expect(withHexAlpha('hsl(120, 50%, 50%)', '88')).toBe(`rgba(64,191,64,${0x88 / 255})`);
        expect(withHexAlpha('rgb(59, 130, 246)', '44')).toBe(`rgba(59,130,246,${0x44 / 255})`);
        // Eight digits are not six: appending would make a ten-digit hex.
        expect(withHexAlpha('#16a34a80', '44')).toBe(`rgba(22,163,74,${0x44 / 255})`);
        expect(withHexAlpha('oklch(0.62 0.19 145)', '88')).toBe(`oklch(0.62 0.19 145 / ${0x88 / 255})`);
        // The ends of the scale.
        expect(withHexAlpha('#abc', 'ff')).toBe('rgba(170,187,204,1)');
        expect(withHexAlpha('#abc', '00')).toBe('rgba(170,187,204,0)');
    });

    it('a colour that cannot carry an alpha stays opaque rather than corrupted', () => {
        expect(withHexAlpha('red', '88')).toBe('red');
        expect(withHexAlpha('var(--lf-area)', '44')).toBe('var(--lf-area)');
    });

    it('never yields the concatenation, nor a NaN, on a colour that is not #rrggbb', () => {
        for (const color of ['#abc', '#ABCD', '#16a34a80', 'hsl(120, 50%, 50%)', 'rgb(59, 130, 246)', 'oklch(0.62 0.19 145)', 'red']) {
            for (const alphaHex of ['88', '44']) {
                const out = withHexAlpha(color, alphaHex);
                expect(out, `${color} + ${alphaHex}`).not.toBe(color + alphaHex);
                expect(out, `${color} + ${alphaHex}`).not.toContain('NaN');
            }
        }
    });
});

describe('parseRgba — the channels of a colour and the opacity it carries', () => {
    it('reads an opaque notation with alpha 1, its channels those of parseRgb', () => {
        for (const color of ['#1a4031', '#1A4031', '#abc', 'rgb(22, 163, 74)', 'rgb(22 163 74)', 'rgba(22, 163, 74)', 'hsl(120, 50%, 50%)', ' #1a4031 ']) {
            expect(parseRgba(color), color).toEqual({...parseRgb(color), alpha: 1});
            expect(parseRgb(color), `barrier: ${color} is a colour parseRgb reads`).not.toBeNull();
        }
    });

    it('reads the alpha of an eight-digit and a four-digit hex, byte by byte', () => {
        expect(parseRgba('#16a34a80')).toEqual({r: 22, g: 163, b: 74, alpha: 0x80 / 255});
        expect(parseRgba('#1A4031FF')).toEqual({r: 26, g: 64, b: 49, alpha: 1});
        expect(parseRgba('#ef444400')).toEqual({r: 239, g: 68, b: 68, alpha: 0});
        // The fourth digit is doubled, like the three before it: #abcd is #aabbccdd.
        expect(parseRgba('#abcd')).toEqual({r: 170, g: 187, b: 204, alpha: 0xdd / 255});
    });

    it('reads the fourth number of rgba() and hsla(), comma or space syntax, after a slash, as a number or a percentage', () => {
        expect(parseRgba('rgba(22, 163, 74, 0.3)')).toEqual({r: 22, g: 163, b: 74, alpha: 0.3});
        expect(parseRgba('RGBA(22,163,74,.3)')).toEqual({r: 22, g: 163, b: 74, alpha: 0.3});
        expect(parseRgba('rgb(22 163 74 / 0.3)')).toEqual({r: 22, g: 163, b: 74, alpha: 0.3});
        expect(parseRgba('rgb(22 163 74 / 30%)')).toEqual({r: 22, g: 163, b: 74, alpha: 0.3});
        expect(parseRgba('hsla(120, 50%, 50%, 0.25)')).toEqual({r: 64, g: 191, b: 64, alpha: 0.25});
        expect(parseRgba('hsl(120deg 50% 50% / 25%)')).toEqual({r: 64, g: 191, b: 64, alpha: 0.25});
    });

    it('clamps an alpha outside 0–1 to its end', () => {
        expect(parseRgba('rgba(1, 2, 3, 1.5)')?.alpha).toBe(1);
        expect(parseRgba('rgba(1, 2, 3, -0.5)')?.alpha).toBe(0);
        expect(parseRgba('rgb(1 2 3 / 150%)')?.alpha).toBe(1);
        expect(parseRgba('rgb(1 2 3 / -20%)')?.alpha).toBe(0);
    });

    it('refuses what parseRgb refuses — a name, var(), color-mix(), oklch(), a broken hex — and an alpha it cannot read', () => {
        for (const color of ['red', 'transparent', 'var(--lf-surface-card)', 'color-mix(in oklab, #fff 50%, #000)', 'oklch(0.62 0.19 145 / 0.5)', '#12345', '#gggggg', '', 'rgb(1, 2)']) {
            expect(parseRgb(color), `barrier: parseRgb refuses ${JSON.stringify(color)}`).toBeNull();
            expect(parseRgba(color), JSON.stringify(color)).toBeNull();
        }
        // The channels read, the alpha does not: unreadable, never taken for opaque.
        expect(parseRgb('rgba(1, 2, 3, abc)'), 'barrier: the channels alone are readable').not.toBeNull();
        expect(parseRgba('rgba(1, 2, 3, abc)')).toBeNull();
    });
});
