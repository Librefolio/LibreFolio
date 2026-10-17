/**
 * The colour arithmetic of the category charts — the one home for it: a mix in OKLab, the shades of a family (GR4) and
 * the rounds past the end of a sequence (GR5), and the colour a continuous scale draws between two of its stops. The
 * contrast that picks a readable text lives in `./contrast`.
 *
 * **GR4, the subtypes of a family**: the designer's round 2, mixing rule (developer, D-T17, 15/10/2026).
 * - Light theme: toward white, at 15, 30 and 45 %.
 * - Dark theme: toward the card (`--lf-surface-card`), at 18, 32 and 45 %, so a shade never washes out.
 * - From the fourth subtype on (the ETF family has six), the same steps toward the opposite pole: in the light theme
 *   `#1C2420`, the round-2 primary text of the designer's role table; white in the dark theme (decision 2,
 *   15/10/2026). Both light poles are literals, as the designer wrote them, so the shades do not move with
 *   tokens.css; only the dark theme's near pole is a role, read live. Between the seven members of a full family
 *   CIEDE2000 falls to 3.2–6.0 at worst: a known limit, for round 3.
 *
 * The mix is computed in OKLab, like the derived roles of tokens.css (`color-mix(in oklab, …)`, D-T5): the first step
 * moves a shade 6.5–9.9 CIEDE2000 from its base, against 5.6–8.6 for the same mix in sRGB.
 *
 * **GR5, past the end of a sequence**: the next round of the same colours, one shade further, never a silent repeat.
 *
 * @module lib/theme/chartShades
 */

import {parseRgb, type Rgb} from './colorAlpha';
import {srgbToLinear} from './contrast';

/** Where the shades of a family go, and by how much: the near pole for the first steps, the far one after them. */
export interface ShadePoles {
    near: string;
    far: string;
    /** Share of the pole in each shade, step by step. */
    steps: readonly number[];
}

const LIGHT_SHADES = {near: '#FFFFFF', far: '#1C2420', steps: [0.15, 0.3, 0.45]} as const;
const DARK_SHADES = {far: '#FFFFFF', steps: [0.18, 0.32, 0.45]} as const;

/** The GR4 poles of the active theme. `card` is the dark theme's near pole, the card the chart sits on. */
export function shadePoles(dark: boolean, card: string): ShadePoles {
    return dark ? {near: card, far: DARK_SHADES.far, steps: DARK_SHADES.steps} : {near: LIGHT_SHADES.near, far: LIGHT_SHADES.far, steps: LIGHT_SHADES.steps};
}

function toChannel(linear: number): number {
    const value = linear <= 0.0031308 ? 12.92 * linear : 1.055 * linear ** (1 / 2.4) - 0.055;
    return Math.round(Math.min(1, Math.max(0, value)) * 255);
}

function toHex({r, g, b}: Rgb): string {
    return `#${[r, g, b].map((channel) => channel.toString(16).padStart(2, '0')).join('')}`;
}

type Oklab = [number, number, number];

function toOklab({r, g, b}: Rgb): Oklab {
    const [lr, lg, lb] = [srgbToLinear(r), srgbToLinear(g), srgbToLinear(b)];
    const l = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb);
    const m = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
    const s = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);
    return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s, 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s];
}

function fromOklab([L, a, b]: Oklab): Rgb {
    const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
    const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
    const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
    return {
        r: toChannel(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
        g: toChannel(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
        b: toChannel(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s),
    };
}

/**
 * `from` mixed toward `to`, `amount` of the way (0–1), in OKLab; as `#rrggbb`, out-of-gamut channels clipped. `from`
 * comes back unchanged when either colour is not parseable: a shade equal to its base is a better failure than a black.
 */
export function mixOklab(from: string, to: string, amount: number): string {
    const start = parseRgb(from);
    const end = parseRgb(to);
    if (!start || !end) return from;
    const [a, b] = [toOklab(start), toOklab(end)];
    return toHex(fromOklab([0, 1, 2].map((i) => a[i] + (b[i] - a[i]) * amount) as Oklab));
}

/**
 * The colour of the member of rank `rank` in a family whose base colour is `base` (GR4): 0 is the base itself, 1–3 the
 * steps toward the near pole, 4–6 the same steps toward the far pole. Past the sixth the cycle starts again. A sequence
 * that runs out of colours takes its next round from here too (GR5, `sequenceColor` in `./chartCategories`).
 */
export function familyShade(base: string, rank: number, poles: ShadePoles): string {
    if (rank <= 0) return base;
    const count = poles.steps.length;
    const cycle = (rank - 1) % (2 * count);
    return mixOklab(base, cycle < count ? poles.near : poles.far, poles.steps[cycle % count]);
}

/**
 * The colour a continuous scale draws for `value` on [`min`, `max`], its stops evenly spaced: channel by channel in
 * sRGB between the two nearest stops, as ECharts' `visualMap` interpolates them. As `#rrggbb`; the nearest stop when a
 * colour is not parseable.
 */
export function scaleColor(stops: readonly string[], value: number, min: number, max: number): string {
    const position = (Math.min(max, Math.max(min, value)) - min) / (max - min || 1);
    const scaled = position * (stops.length - 1);
    const index = Math.min(stops.length - 2, Math.floor(scaled));
    const t = scaled - index;
    const start = parseRgb(stops[index]);
    const end = parseRgb(stops[index + 1]);
    if (!start || !end) return stops[Math.round(scaled)];
    const lerp = (a: number, b: number) => Math.round(a + (b - a) * t);
    return toHex({r: lerp(start.r, end.r), g: lerp(start.g, end.g), b: lerp(start.b, end.b)});
}
