/**
 * contrast — the app's one WCAG home (`$lib/theme/contrast`): the formulas of the colour gate
 * (`scripts/theme/theme-roles.mjs`), for the charts that pick a readable text at draw time.
 *
 * - **Golden ratios**, from outside the module: white on black is 21, white on the STOCK violet 7.10 (the DV
 *   analysis's independent implementation), and the two greys every accessibility checker quotes, `#767676` at 4.54
 *   and `#777777` at 4.48 on white.
 * - **A translucent colour is composited first**, over the card it is drawn on: the same translucent black reads as a
 *   grey on a white card and as black on a black one. Where the composite lands on a whole byte it is checked against
 *   that byte written by hand (black at 20 % over white is `#cccccc`), so the compositing is not checked by itself.
 * - **The edges**: a colour, or a card, that cannot be parsed measures 1; a tie between two texts keeps the first.
 *
 * Node env: pure functions, no DOM. Moved here from `chartShades.test.ts` with the functions (T's review of the bridge).
 *
 * @module lib/theme/contrast.test
 */
import {describe, expect, it} from 'vitest';

import {contrastRatio, over, readableOn, relativeLuminance, srgbToLinear} from './contrast';

describe('srgbToLinear — the sRGB transfer function, per channel', () => {
    it('maps the ends to 0 and 1, and mid grey to its published linear value', () => {
        expect(srgbToLinear(0)).toBe(0);
        expect(srgbToLinear(255)).toBeCloseTo(1, 12);
        expect(srgbToLinear(128)).toBeCloseTo(0.2158605, 6);
    });

    it('takes the linear segment at and below the knee (0.04045) and the power curve above it', () => {
        expect(srgbToLinear(10), '10/255 = 0.0392: linear').toBeCloseTo(10 / 255 / 12.92, 12);
        expect(srgbToLinear(11), '11/255 = 0.0431: power curve').toBeCloseTo(((11 / 255 + 0.055) / 1.055) ** 2.4, 12);
    });
});

describe('relativeLuminance — WCAG 2.x', () => {
    it('weighs the three primaries 0.2126, 0.7152 and 0.0722, and spans black 0 to white 1', () => {
        expect(relativeLuminance({r: 0, g: 0, b: 0})).toBe(0);
        expect(relativeLuminance({r: 255, g: 255, b: 255})).toBeCloseTo(1, 12);
        expect(relativeLuminance({r: 255, g: 0, b: 0})).toBeCloseTo(0.2126, 12);
        expect(relativeLuminance({r: 0, g: 255, b: 0})).toBeCloseTo(0.7152, 12);
        expect(relativeLuminance({r: 0, g: 0, b: 255})).toBeCloseTo(0.0722, 12);
    });
});

describe('over — a colour composited over an opaque one', () => {
    const WHITE = {r: 255, g: 255, b: 255};

    it('keeps an opaque colour, lets a transparent one vanish, and weighs the two by alpha in between', () => {
        expect(over({r: 10, g: 20, b: 30, alpha: 1}, WHITE)).toEqual({r: 10, g: 20, b: 30});
        expect(over({r: 10, g: 20, b: 30, alpha: 0}, WHITE)).toEqual(WHITE);

        const grey = over({r: 0, g: 0, b: 0, alpha: 0.2}, WHITE);
        for (const channel of [grey.r, grey.g, grey.b]) expect(channel, 'black at 20 % over white: 255 × 0.8').toBeCloseTo(204, 9);
    });
});

describe('contrastRatio — WCAG 2.x, 1 to 21', () => {
    it('measures 21 between white and black, either way round, and 1 between a colour and itself', () => {
        expect(contrastRatio('#FFFFFF', '#000000')).toBeCloseTo(21, 10);
        expect(contrastRatio('#000000', '#FFFFFF')).toBeCloseTo(21, 10);
        expect(contrastRatio('#FFFFFF', '#ffffff')).toBe(1);
        expect(contrastRatio('#1D5BD8', '#1D5BD8')).toBe(1);
    });

    it('measures white on the STOCK violet as the independent implementation does: 7.10', () => {
        expect(contrastRatio('#FFFFFF', '#6D28D9').toFixed(2)).toBe('7.10');
    });

    it('measures the two greys of the AA threshold as every checker quotes them: #767676 4.54, #777777 4.48 on white', () => {
        expect(contrastRatio('#767676', '#ffffff').toFixed(2)).toBe('4.54');
        expect(contrastRatio('#777777', '#ffffff').toFixed(2)).toBe('4.48');
    });

    it('composites a translucent colour over the card first: black at 20 % is #cccccc on white and #000000 on black', () => {
        expect(contrastRatio('rgba(0, 0, 0, 0.2)', '#000000', '#ffffff')).toBeCloseTo(contrastRatio('#cccccc', '#000000'), 9);
        expect(contrastRatio('#00000033', '#000000', '#ffffff'), 'the same alpha in #rrggbbaa: 0x33 is 20 %').toBeCloseTo(contrastRatio('#cccccc', '#000000'), 9);
        expect(contrastRatio('rgba(0, 0, 0, 0.2)', '#ffffff', '#000000'), 'over a black card it stays black').toBeCloseTo(21, 9);
        expect(contrastRatio('rgba(255, 255, 255, 0.2)', '#000000', '#000000'), 'white at 20 % over black: 255 × 0.2 = 51').toBeCloseTo(contrastRatio('#333333', '#000000'), 9);
    });

    it('takes a white card when none is given, measures an opaque colour without it, and treats a translucent card as opaque', () => {
        expect(contrastRatio('rgba(0, 0, 0, 0.2)', '#000000'), 'no card: white').toBeCloseTo(contrastRatio('rgba(0, 0, 0, 0.2)', '#000000', '#ffffff'), 12);
        expect(contrastRatio('#ffffff', '#000000', '#123456'), 'opaque colours: the card plays no part').toBeCloseTo(21, 10);
        expect(contrastRatio('rgba(0, 0, 0, 0.2)', '#000000', 'rgba(255, 255, 255, 0.5)'), 'a translucent card counts as its opaque colour').toBeCloseTo(contrastRatio('rgba(0, 0, 0, 0.2)', '#000000', '#ffffff'), 12);
    });

    it('answers 1 when a colour or the card cannot be parsed: no contrast is claimed for what cannot be measured', () => {
        expect(contrastRatio('#FFFFFF', '#000000'), 'barrier: the same pair, parseable, is measured').toBeGreaterThan(1);
        expect(contrastRatio('not a colour', '#000000')).toBe(1);
        expect(contrastRatio('#FFFFFF', 'oklch(0.2 0 0)')).toBe(1);
        expect(contrastRatio('#FFFFFF', '#000000', 'var(--lf-surface-card)')).toBe(1);
    });
});

describe('readableOn — the candidate that reads best', () => {
    it('picks the highest contrast, wherever it sits in the list', () => {
        expect(readableOn('#ffffff', ['#eeeeee', '#000000'])).toBe('#000000');
        expect(readableOn('#000000', ['#111111', '#ffffff', '#222222'])).toBe('#ffffff');
    });

    it('keeps the first candidate on a tie, in either order', () => {
        expect(readableOn('#777777', ['#FFFFFF', '#ffffff'])).toBe('#FFFFFF');
        expect(readableOn('#777777', ['#ffffff', '#FFFFFF'])).toBe('#ffffff');
        expect(readableOn('#777777', ['nope', 'oklch(0 0 0)']), 'two candidates it cannot measure tie at 1').toBe('nope');
    });

    it('hands back a lone candidate', () => {
        expect(readableOn('#ffffff', ['#fefefe'])).toBe('#fefefe');
    });

    it('measures a translucent background over the card: a half-black veil reads dark text on white, light text on black', () => {
        const veil = 'rgba(0, 0, 0, 0.5)';
        expect(readableOn(veil, ['#000000', '#ffffff'], '#ffffff'), 'over white the veil is a mid grey: black reads better').toBe('#000000');
        expect(readableOn(veil, ['#000000', '#ffffff'], '#000000'), 'over black the veil is black: white reads better').toBe('#ffffff');
        expect(readableOn(veil, ['#000000', '#ffffff']), 'no card: white').toBe('#000000');
    });
});
