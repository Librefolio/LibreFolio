/**
 * WCAG contrast for the colours the app computes at run time — the one home for it in the app's code.
 *
 * Two implementations already sit outside the app: the colour gate's (`scripts/theme/theme-roles.mjs`, on tokens.css)
 * and the Designer Lab's (`lib/dev/designer-lab`, debug builds only). This module is the app's own, for the charts that
 * pick a readable text at draw time; the Lab is to import it (L-15): debug code may import production code, never the
 * other way round. Same formulas as the gate: WCAG 2.x relative luminance, and a translucent colour composited over an
 * opaque one before it is measured.
 *
 * @module lib/theme/contrast
 */

import {parseRgba, type Rgb, type Rgba} from './colorAlpha';

/** An sRGB channel (0–255) as linear light (0–1). */
export function srgbToLinear(channel: number): number {
    const value = channel / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

/** The WCAG 2.x relative luminance of an opaque sRGB colour, 0 (black) to 1 (white). */
export function relativeLuminance({r, g, b}: Rgb): number {
    return 0.2126 * srgbToLinear(r) + 0.7152 * srgbToLinear(g) + 0.0722 * srgbToLinear(b);
}

/** A colour over an opaque one, as the browser composites it. */
export function over(top: Rgba, bottom: Rgb): Rgb {
    const a = top.alpha;
    return {r: top.r * a + bottom.r * (1 - a), g: top.g * a + bottom.g * (1 - a), b: top.b * a + bottom.b * (1 - a)};
}

/**
 * The WCAG 2.x contrast ratio of two colours, 1 to 21. A translucent one is first composited over `card`, the opaque
 * surface it is drawn on (a translucent `card` counts as opaque). 1 when a colour is not parseable.
 */
export function contrastRatio(first: string, second: string, card = '#ffffff'): number {
    const a = parseRgba(first);
    const b = parseRgba(second);
    const base = parseRgba(card);
    if (!a || !b || !base) return 1;
    const opaque = (colour: Rgba): Rgb => (colour.alpha < 1 ? over(colour, base) : colour);
    const [high, low] = [relativeLuminance(opaque(a)), relativeLuminance(opaque(b))].sort((x, y) => y - x);
    return (high + 0.05) / (low + 0.05);
}

/** The candidate that reads best on `background` (composited over `card` when translucent): the first on a tie. */
export function readableOn(background: string, candidates: readonly [string, ...string[]], card?: string): string {
    return candidates.reduce((best, candidate) => (contrastRatio(background, candidate, card) > contrastRatio(background, best, card) ? candidate : best));
}
