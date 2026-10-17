/**
 * Designer Lab — colour parsing, conversion and contrast (`color.js`).
 *
 * One module serves the build-time scanner (Node) and the live engines (browser): the catalogue keys, the CSSOM and
 * ECharts rewrites and the contrast panel all rest on these functions agreeing about what a colour is. The expected
 * values below are independent of the code: byte values of the hex spelling, the WCAG figures quoted in the analysis
 * (2.54:1 for `#9ca3af` on white) and P11 (`#ef4444` = `oklch(63.68% 0.2078 25.33)`).
 */

import {describe, expect, it, vi} from 'vitest';
import {clampToSrgb, colorKey, contrastRatio, formatOklch, inSrgbGamut, oklchToRgba, parseColor, replaceColorTokens, rgbaToOklch, toCanvasColor, toHex, type Rgba} from './color.js';

/** Tailwind v4 emerald-600: a colour outside sRGB (its red channel is negative). */
const EMERALD_600 = 'oklch(59.6% .145 163.225)';

/** A colour the parser must accept: the test fails here, with the input, rather than on a null later. */
function must(text: string): Rgba {
    const rgba = parseColor(text);
    if (!rgba) throw new Error(`parseColor rejected ${text}`);
    return rgba;
}

/** 8-bit channels and a 3-decimal alpha: how the expected values are written. */
const bytes = (rgba: Rgba | null): number[] | null => (rgba ? [Math.round(rgba.r * 255), Math.round(rgba.g * 255), Math.round(rgba.b * 255), Math.round(rgba.alpha * 1000) / 1000] : null);

/** Channel by channel, to `digits` decimals: 9 for two spellings of one value, 6 across a conversion and back (the OKLab matrices carry 10 digits). */
function expectSameColor(actual: Rgba, expected: Rgba, label: string, digits = 9): void {
    expect(actual.r, `${label} r`).toBeCloseTo(expected.r, digits);
    expect(actual.g, `${label} g`).toBeCloseTo(expected.g, digits);
    expect(actual.b, `${label} b`).toBeCloseTo(expected.b, digits);
    expect(actual.alpha, `${label} alpha`).toBeCloseTo(expected.alpha, digits);
}

describe('parseColor', () => {
    it('reads hex literals of 3, 4, 6 and 8 digits, in either case', () => {
        expect(bytes(parseColor('#fff'))).toEqual([255, 255, 255, 1]);
        expect(bytes(parseColor('#abc'))).toEqual([170, 187, 204, 1]);
        expect(bytes(parseColor('#f008'))).toEqual([255, 0, 0, 0.533]);
        expect(bytes(parseColor('#1e293b'))).toEqual([30, 41, 59, 1]);
        expect(bytes(parseColor('#1E293B'))).toEqual([30, 41, 59, 1]);
        expect(bytes(parseColor('#1e293bf2'))).toEqual([30, 41, 59, 0.949]);
        expect(bytes(parseColor('  #1e293b  '))).toEqual([30, 41, 59, 1]);
    });

    it('reads rgb()/rgba() in the legacy comma form and in the modern space form, with `/ alpha` and percentages', () => {
        expect(bytes(parseColor('rgb(30, 41, 59)'))).toEqual([30, 41, 59, 1]);
        expect(bytes(parseColor('rgba(30,41,59,.95)'))).toEqual([30, 41, 59, 0.95]);
        expect(bytes(parseColor('rgba(0, 0, 0, 40%)'))).toEqual([0, 0, 0, 0.4]);
        expect(bytes(parseColor('RGBA(30, 41, 59, 1)'))).toEqual([30, 41, 59, 1]);
        expect(bytes(parseColor('rgb(30 41 59)'))).toEqual([30, 41, 59, 1]);
        expect(bytes(parseColor('rgb(30 41 59 / 0.5)'))).toEqual([30, 41, 59, 0.5]);
        expect(bytes(parseColor('rgb(30 41 59 / 25%)'))).toEqual([30, 41, 59, 0.25]);
        expect(bytes(parseColor('rgb(100% 0% 50%)'))).toEqual([255, 0, 128, 1]);
        // Alpha is clamped to 0..1.
        expect(bytes(parseColor('rgb(0 0 0 / 150%)'))).toEqual([0, 0, 0, 1]);
    });

    it('reads hsl()/hsla(), legacy and modern, with hue units', () => {
        expect(bytes(parseColor('hsl(0, 100%, 50%)'))).toEqual([255, 0, 0, 1]);
        expect(bytes(parseColor('hsla(120, 100%, 50%, 0.5)'))).toEqual([0, 255, 0, 0.5]);
        expect(bytes(parseColor('hsl(240 100% 50% / 25%)'))).toEqual([0, 0, 255, 0.25]);
        // The modern syntax allows bare numbers for saturation and lightness, on a 0..100 scale.
        expect(bytes(parseColor('hsl(240 100 50)'))).toEqual([0, 0, 255, 1]);
        expect(bytes(parseColor('hsl(120deg 100% 50%)'))).toEqual([0, 255, 0, 1]);
        expect(bytes(parseColor('hsl(0.5turn 100% 50%)'))).toEqual([0, 255, 255, 1]);
        expect(bytes(parseColor('hsl(-120 100% 50%)'))).toEqual([0, 0, 255, 1]);
    });

    it('reads oklch() with the lightness as a percentage or a number, and a percentage chroma worth 0.4', () => {
        const reference = must('oklch(0.5 0.1 180)');
        for (const spelling of ['oklch(50% 0.1 180)', 'oklch(50% 25% 180)', 'oklch(0.5 .1 180deg)', 'OKLCH(50% 0.1 0.5turn)']) expectSameColor(must(spelling), reference, spelling);
        expect(must('oklch(50% 0.1 180 / 50%)').alpha).toBe(0.5);
        expect(bytes(parseColor('oklch(100% 0 0)'))).toEqual([255, 255, 255, 1]);
        expect(bytes(parseColor('oklch(0% 0 0)'))).toEqual([0, 0, 0, 1]);
    });

    it('reads oklab(), with percentages worth 0.4 on a and b', () => {
        expect(bytes(parseColor('oklab(1 0 0)'))).toEqual([255, 255, 255, 1]);
        expect(bytes(parseColor('oklab(0 0 0)'))).toEqual([0, 0, 0, 1]);
        expectSameColor(must('oklab(50% 25% -25%)'), must('oklab(0.5 0.1 -0.1)'), 'oklab percentages');
        expect(must('oklab(0.5 0.1 -0.1 / 0.3)').alpha).toBe(0.3);
    });

    it('reads color() in srgb, srgb-linear and display-p3', () => {
        expect(bytes(parseColor('color(srgb 1 0 0)'))).toEqual([255, 0, 0, 1]);
        expect(bytes(parseColor('color(srgb 100% 0% 0% / 50%)'))).toEqual([255, 0, 0, 0.5]);
        expect(bytes(parseColor('color(srgb-linear 1 0 0)'))).toEqual([255, 0, 0, 1]);
        // Linear 0.5 is sRGB 0.7354 (the transfer function, not a scale).
        expect(must('color(srgb-linear 0.5 0.5 0.5)').r).toBeCloseTo(0.7354, 3);
        const p3White = must('color(display-p3 1 1 1)');
        for (const channel of [p3White.r, p3White.g, p3White.b]) expect(channel).toBeCloseTo(1, 4);
        // Display-p3 red is wider than sRGB: it parses, outside the gamut.
        const p3Red = must('color(display-p3 1 0 0)');
        expect(p3Red.r).toBeGreaterThan(1);
        expect(inSrgbGamut(p3Red)).toBe(false);
    });

    it('reads the keywords white, black and transparent', () => {
        expect(bytes(parseColor('white'))).toEqual([255, 255, 255, 1]);
        expect(bytes(parseColor('Black'))).toEqual([0, 0, 0, 1]);
        expect(bytes(parseColor('transparent'))).toEqual([0, 0, 0, 0]);
    });

    it('gives null for expressions and for anything that is not a colour', () => {
        const rejected = [
            'var(--theme-accent)',
            'rgb(var(--r), 0, 0)',
            'rgb(var(--r) 0 0 / 50%)',
            'calc(1px + 2px)',
            'rgb(calc(10 + 20) 0 0)',
            'color-mix(in srgb, #fff 50%, transparent)',
            'oklch(from var(--x) l c h)',
            '',
            'not a colour',
            '#12',
            '#12345',
            '#ggg',
            'rgb(1, 2)',
            'rgb(1,,2,3)',
            'rgb(a, b, c)',
            'rgb(1 2 3 / x)',
            'hsl(x, 1%, 2%)',
            'oklch(50% 0.1)',
            'color(srgb 1 0)',
            'color(rec2020 1 0 0)',
        ];
        for (const text of rejected) expect(parseColor(text), JSON.stringify(text)).toBeNull();
    });
});

describe('colorKey', () => {
    it('gives every spelling of an sRGB colour the same #rrggbb key, alpha left out', () => {
        for (const spelling of ['#1e293b', '#1E293B', 'rgb(30, 41, 59)', 'rgba(30,41,59,.95)', 'rgb(30 41 59 / 10%)', '#1e293b80', 'color(srgb 0.11765 0.16078 0.23137)']) {
            expect(colorKey(must(spelling)), spelling).toBe('#1e293b');
        }
    });

    it('keys an in-gamut oklch() like its hex spelling', () => {
        expect(colorKey(must('oklch(100% 0 0)'))).toBe('#ffffff');
        expect(colorKey(must('oklch(63.68% 0.2078 25.33)'))).toBe('#ef4444');
    });

    it('keys a colour outside sRGB by its rounded OKLCH, the same for every spelling of it', () => {
        const emerald = must(EMERALD_600);
        expect(inSrgbGamut(emerald)).toBe(false);
        expect(colorKey(emerald)).toBe('oklch(0.596 0.145 163.2)');
        expect(colorKey(must('oklch(0.596 0.145 163.225)'))).toBe(colorKey(emerald));
        expect(colorKey(must('oklch(59.6% 36.25% 163.225deg / 50%)'))).toBe(colorKey(emerald));
    });
});

describe('OKLCH conversions and the sRGB gamut', () => {
    it('converts #ef4444 to oklch(63.68% 0.2078 25.33) and back (P11 of the analysis)', () => {
        const red = must('#ef4444');
        const oklch = rgbaToOklch(red);
        expect(formatOklch(oklch)).toBe('oklch(63.68% 0.2078 25.33)');
        expect(formatOklch({...oklch, alpha: 0.5})).toBe('oklch(63.68% 0.2078 25.33 / 0.5)');
        expectSameColor(oklchToRgba(oklch.l, oklch.c, oklch.h, oklch.alpha), red, 'round trip', 6);
        // The rounded spelling, as Tailwind writes it, lands on the same 8-bit colour.
        expect(toHex(must('oklch(63.68% 0.2078 25.33)'))).toBe('#ef4444');
    });

    it('gives a grey no chroma and hue 0', () => {
        const grey = rgbaToOklch(must('#808080'));
        expect(grey.c).toBeLessThan(1e-6);
        expect(grey.h).toBe(0);
    });

    it('tolerates half an 8-bit step outside 0..1 by default, nothing with eps 0', () => {
        expect(inSrgbGamut({r: 0, g: 0.5, b: 1, alpha: 1})).toBe(true);
        expect(inSrgbGamut({r: 1 + 0.4 / 255, g: 0, b: 0, alpha: 1})).toBe(true);
        expect(inSrgbGamut({r: 1 + 0.6 / 255, g: 0, b: 0, alpha: 1})).toBe(false);
        expect(inSrgbGamut({r: -0.6 / 255, g: 0, b: 0, alpha: 1})).toBe(false);
        expect(inSrgbGamut({r: 1 + 0.4 / 255, g: 0, b: 0, alpha: 1}, 0)).toBe(false);
    });

    it('brings a colour into sRGB keeping its OKLCH lightness and hue, and leaves an sRGB colour alone', () => {
        for (const text of [EMERALD_600, 'color(display-p3 1 0 0)', 'oklch(70% 0.3 300 / 0.4)']) {
            const original = must(text);
            const clamped = clampToSrgb(original);
            const before = rgbaToOklch(original);
            const after = rgbaToOklch(clamped);
            expect(inSrgbGamut(clamped, 0), text).toBe(true);
            expect(after.l, `${text} lightness`).toBeCloseTo(before.l, 3);
            expect(Math.abs(after.h - before.h), `${text} hue`).toBeLessThan(0.5);
            expect(after.c, `${text} chroma`).toBeLessThan(before.c);
            expect(clamped.alpha, `${text} alpha`).toBe(original.alpha);
        }
        const inside = must('#1e293b');
        expect(clampToSrgb(inside)).toBe(inside);
        // Beyond white and below black there is no chroma left to trade.
        expect(toHex(clampToSrgb({r: 1.2, g: 1.2, b: 1.2, alpha: 1}))).toBe('#ffffff');
    });
});

describe('serialisation', () => {
    it('writes #rrggbb, with the alpha byte only for a translucent colour that asks for it', () => {
        expect(toHex(must('rgb(30, 41, 59)'))).toBe('#1e293b');
        expect(toHex(must('rgba(30, 41, 59, 0.5)'))).toBe('#1e293b80');
        expect(toHex(must('rgba(30, 41, 59, 0.5)'), false)).toBe('#1e293b');
        expect(toHex(must('color(display-p3 1 0 0)'))).toMatch(/^#[0-9a-f]{6}$/);
    });

    it('writes a canvas colour as #rrggbb when opaque and rgba() when translucent, clamped to sRGB', () => {
        expect(toCanvasColor(must('#1E293B'))).toBe('#1e293b');
        expect(toCanvasColor(must('rgba(30,41,59,.95)'))).toBe('rgba(30, 41, 59, 0.95)');
        expect(toCanvasColor(must('rgba(0, 0, 0, 0.12345)'))).toBe('rgba(0, 0, 0, 0.123)');
        // Canvas libraries read no oklch(): an out-of-gamut colour is clamped.
        expect(toCanvasColor(must(EMERALD_600))).toMatch(/^#[0-9a-f]{6}$/);
        expect(toCanvasColor(must('oklch(59.6% .145 163.225 / 0.5)'))).toMatch(/^rgba\(\d{1,3}, \d{1,3}, \d{1,3}, 0\.5\)$/);
    });
});

describe('contrastRatio (WCAG 2)', () => {
    const white = must('#fff');
    const black = must('#000');

    it('gives 21:1 for white on black either way, 1:1 for a colour on itself', () => {
        expect(contrastRatio(white, black)).toBeCloseTo(21, 10);
        expect(contrastRatio(black, white)).toBeCloseTo(21, 10);
        expect(contrastRatio(white, white)).toBe(1);
    });

    it('gives 2.54:1 for #9ca3af on white', () => {
        expect(contrastRatio(must('#9ca3af'), white)).toBeCloseTo(2.54, 2);
    });

    it('composites a translucent foreground over the background, and paints the background opaque', () => {
        const halfBlack = must('rgba(0, 0, 0, 0.5)');
        expect(contrastRatio(halfBlack, white)).toBeCloseTo(contrastRatio({r: 0.5, g: 0.5, b: 0.5, alpha: 1}, white), 10);
        expect(contrastRatio(halfBlack, white)).toBeLessThan(contrastRatio(black, white));
        expect(contrastRatio(black, {...white, alpha: 0.2})).toBeCloseTo(21, 10);
    });
});

describe('replaceColorTokens', () => {
    const toSurface = (rgba: Rgba): string | null => (colorKey(rgba) === '#1e293b' ? 'var(--surface)' : null);

    it('replaces the colour tokens of a CSS value and of HTML, matched by parsed colour', () => {
        expect(replaceColorTokens('1px solid #1e293b', toSurface)).toBe('1px solid var(--surface)');
        expect(replaceColorTokens('linear-gradient(#1E293B, rgba(30, 41, 59, .5) 40%, #fff)', toSurface)).toBe('linear-gradient(var(--surface), var(--surface) 40%, #fff)');
        expect(replaceColorTokens('<span style="color:#1e293b">-3%</span>', toSurface)).toBe('<span style="color:var(--surface)">-3%</span>');
    });

    it('hands the map each token as written, and keeps it when the map returns null', () => {
        const text = 'a #1e293b b rgba(30, 41, 59, .5) c hsl(0 100% 50% / 0.2) d #1e293b80';
        const seen: string[] = [];
        const out = replaceColorTokens(text, (_rgba, raw) => {
            seen.push(raw);
            return null;
        });
        expect(out).toBe(text);
        expect(seen).toEqual(['#1e293b', 'rgba(30, 41, 59, .5)', 'hsl(0 100% 50% / 0.2)', '#1e293b80']);
    });

    it('never takes an HTML entity, an identifier or an expression for a colour', () => {
        const map = vi.fn(() => 'red');
        const text = '&#123; id#fff &#x1F600; rgb(var(--r) 0 0) color-mix(in srgb, var(--a) 50%, transparent)';
        expect(replaceColorTokens(text, map)).toBe(text);
        expect(replaceColorTokens('', map)).toBe('');
        expect(map).not.toHaveBeenCalled();
    });
});
