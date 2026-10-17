/**
 * The rulers the colour tests measure with: CIEDE2000, the perceptual distance between two `#rrggbb` colours, and
 * OKLCH, the hue and chroma a rule about hues reads.
 *
 * A shared helper beside the other `$test` helpers, so the tests that judge whether two chart colours can be told apart
 * use one ruler, not a copy each. The formula is the one `allocationHierarchy.test.ts` and `allocationRings.test.ts`
 * wrote out (CIE 142-2001, kL = kC = kH = 1, as Sharma, Wu & Dalal (2005) write it), moved here unchanged.
 *
 * OKLCH is Björn Ottosson's OKLab (2020) in polar form: the same sRGB → XYZ step as CIELAB here, then his two matrices
 * and the cube root between them, then the chroma and the hue of `a` and `b`. The round-3 rule of the greens
 * (`chartCategories.test.ts`) reads it: no category hue between 115° and 225°.
 *
 * A ruler is proven before it measures anything: the published data it must reproduce is exported with it
 * (`SHARMA_PAIRS`, `SRGB_LAB`; `OKLAB_XYZ`, `SRGB_OKLCH`), and `src/lib/theme/chartCategories.test.ts` checks each
 * ruler against it before a gate reads a single distance or hue. A test that relies on this module and runs in another
 * suite should check it the same way: the data is here for that.
 *
 * Not a `*.test.ts`, so vitest does not collect it and `check-orphans` does not count it, and every `__tests__`
 * directory is outside coverage (`vitest.config.ts`).
 *
 * @module __tests__/colorDistance
 */

/** A colour in CIELAB, D65 white: `[L*, a*, b*]`. */
export type Lab = readonly [number, number, number];

/** A colour in CIE XYZ, D65 white with Y = 1: `[X, Y, Z]`. */
export type Xyz = readonly [number, number, number];

/** A colour in OKLab: `[L, a, b]`, L from 0 (black) to 1 (white). */
export type Oklab = readonly [number, number, number];

/** A colour in OKLCH: its OKLab lightness, its chroma, and its hue in degrees, 0–360 (0 for a colour with no chroma). */
export interface Oklch {
    L: number;
    C: number;
    h: number;
}

/**
 * `#rrggbb` → CIE XYZ (D65, Y = 1): the sRGB transfer function (IEC 61966-2-1), then the sRGB → XYZ matrix in its
 * seven-digit form, whose rows sum to the D65 white. The one sRGB step of both rulers, proven through `labOf` on
 * `SRGB_LAB`.
 *
 * Throws on anything else: a ruler returning NaN compares false with every floor, and a colour measured with it would
 * pass in silence.
 */
function xyzOf(hex: string): Xyz {
    const match = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex);
    if (!match) throw new Error(`colorDistance: ${hex} is not #rrggbb`);
    const [r, g, b] = match.slice(1).map((channel) => {
        const c = parseInt(channel, 16) / 255;
        return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
    const x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b;
    const y = 0.2126729 * r + 0.7151522 * g + 0.072175 * b;
    const z = 0.0193339 * r + 0.119192 * g + 0.9503041 * b;
    return [x, y, z];
}

/**
 * `#rrggbb` → CIELAB (D65): XYZ as `xyzOf` gives it — white lands on L* 100 with a* = b* = 0 — then CIE 1976 L*a*b*
 * with the exact ε = 216/24389 and κ = 24389/27. Throws on anything that is not `#rrggbb`.
 */
export function labOf(hex: string): Lab {
    const [x, y, z] = xyzOf(hex);
    const f = (t: number) => (t > 216 / 24389 ? Math.cbrt(t) : ((24389 / 27) * t + 16) / 116);
    const [fx, fy, fz] = [f(x / 0.95047), f(y), f(z / 1.08883)];
    return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}

/**
 * CIE XYZ (D65, Y = 1) → OKLab, as Ottosson defines it: his M1 to approximate cone responses, their cube roots, his M2
 * (the matrices of "A perceptual color space for image processing", 2020, as updated on 2021-01-25).
 */
export function oklabOfXyz([X, Y, Z]: Xyz): Oklab {
    const l = Math.cbrt(0.8189330101 * X + 0.3618667424 * Y - 0.1288597137 * Z);
    const m = Math.cbrt(0.0329845436 * X + 0.9293118715 * Y + 0.0361456387 * Z);
    const s = Math.cbrt(0.0482003018 * X + 0.2643662691 * Y + 0.633851707 * Z);
    return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s, 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s];
}

/**
 * `#rrggbb` → OKLCH: `xyzOf`, `oklabOfXyz`, then the chroma `√(a² + b²)` and the hue `atan2(b, a)` in degrees, 0–360.
 * A colour with no chroma at all takes the hue 0; a near-grey keeps the hue its rounding gives it, so a rule about hues
 * reads the chroma first. Throws on anything that is not `#rrggbb`.
 */
export function oklchOf(hex: string): Oklch {
    const [L, a, b] = oklabOfXyz(xyzOf(hex));
    const C = Math.hypot(a, b);
    return {L, C, h: C === 0 ? 0 : ((Math.atan2(b, a) * 180) / Math.PI + 360) % 360};
}

/**
 * CIEDE2000 (CIE 142-2001), kL = kC = kH = 1, written out as Sharma, Wu & Dalal (2005) write it — with the two
 * conventions their test data exists to catch: the hue of a neutral colour is 0 (and so is Δh' beside one), and the mean
 * of two hues more than 180° apart is taken across 0°/360°.
 */
export function ciede2000([L1, a1, b1]: Lab, [L2, a2, b2]: Lab): number {
    const rad = Math.PI / 180;
    const meanC7 = ((Math.hypot(a1, b1) + Math.hypot(a2, b2)) / 2) ** 7;
    const G = 0.5 * (1 - Math.sqrt(meanC7 / (meanC7 + 25 ** 7)));
    const a1p = (1 + G) * a1;
    const a2p = (1 + G) * a2;
    const C1p = Math.hypot(a1p, b1);
    const C2p = Math.hypot(a2p, b2);
    const hueAngle = (b: number, ap: number) => (b === 0 && ap === 0 ? 0 : (Math.atan2(b, ap) / rad + 360) % 360);
    const h1p = hueAngle(b1, a1p);
    const h2p = hueAngle(b2, a2p);

    let dhp = 0;
    if (C1p * C2p !== 0) {
        dhp = h2p - h1p;
        if (dhp > 180) dhp -= 360;
        else if (dhp < -180) dhp += 360;
    }
    const dLp = L2 - L1;
    const dCp = C2p - C1p;
    const dHp = 2 * Math.sqrt(C1p * C2p) * Math.sin((dhp / 2) * rad);

    const meanLp = (L1 + L2) / 2;
    const meanCp = (C1p + C2p) / 2;
    let meanHp: number;
    if (C1p * C2p === 0) meanHp = h1p + h2p;
    else if (Math.abs(h1p - h2p) <= 180) meanHp = (h1p + h2p) / 2;
    else meanHp = h1p + h2p < 360 ? (h1p + h2p + 360) / 2 : (h1p + h2p - 360) / 2;

    const T = 1 - 0.17 * Math.cos((meanHp - 30) * rad) + 0.24 * Math.cos(2 * meanHp * rad) + 0.32 * Math.cos((3 * meanHp + 6) * rad) - 0.2 * Math.cos((4 * meanHp - 63) * rad);
    const meanCp7 = meanCp ** 7;
    const RT = -2 * Math.sqrt(meanCp7 / (meanCp7 + 25 ** 7)) * Math.sin(60 * Math.exp(-(((meanHp - 275) / 25) ** 2)) * rad);
    const SL = 1 + (0.015 * (meanLp - 50) ** 2) / Math.sqrt(20 + (meanLp - 50) ** 2);
    const SC = 1 + 0.045 * meanCp;
    const SH = 1 + 0.015 * meanCp * T;
    return Math.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2 + RT * (dCp / SC) * (dHp / SH));
}

/** The perceptual distance between two `#rrggbb` colours (ΔE00). Under about 10 two slices side by side are confused. */
export function deltaE00(first: string, second: string): number {
    return ciede2000(labOf(first), labOf(second));
}

/** One row of the published test data: two CIELAB colours and the ΔE00 between them, to four decimals. */
export interface SharmaPair {
    pair: number;
    first: Lab;
    second: Lab;
    deltaE: number;
    branch: string;
}

/**
 * Rows of the test data published with the formula's implementation notes — G. Sharma, W. Wu and E. N. Dalal, "The
 * CIEDE2000 color-difference formula: implementation notes, supplementary test data, and mathematical observations",
 * Color Research & Application 30(1), 2005, table 1 — one per branch an implementation gets wrong, and three pairs of
 * real colours away from L* 50.
 */
export const SHARMA_PAIRS: readonly SharmaPair[] = [
    {pair: 1, first: [50, 2.6772, -79.7751], second: [50, 0, -82.7485], deltaE: 2.0425, branch: 'blues near 275°, where the rotation term R_T acts'},
    {pair: 7, first: [50, 0, 0], second: [50, -1, 2], deltaE: 2.3669, branch: "a neutral colour: its hue is 0, and so is Δh'"},
    {pair: 10, first: [50, 2.49, -0.001], second: [50, -2.49, 0.001], deltaE: 7.1792, branch: 'two hues 180° apart, their mean on one side of 0°/360°'},
    {pair: 11, first: [50, 2.49, -0.001], second: [50, -2.49, 0.0011], deltaE: 7.2195, branch: 'the same, 0.0001 away, on the other side — the branch most implementations get wrong'},
    {pair: 13, first: [50, -0.001, 2.49], second: [50, 0.0009, -2.49], deltaE: 4.8045, branch: 'two hues 180° apart across the b* axis, their sum under 360°'},
    {pair: 17, first: [50, 2.5, 0], second: [73, 25, -18], deltaE: 27.1492, branch: 'a large difference, its lightness weighted by S_L away from L* 50'},
    {pair: 25, first: [60.2574, -34.0099, 36.2677], second: [60.4626, -34.1751, 39.4387], deltaE: 1.2644, branch: 'two real greens'},
    {pair: 31, first: [90.8027, -2.0831, 1.441], second: [91.1528, -1.6435, 0.0447], deltaE: 1.4441, branch: 'two near-whites, L* past 90'},
    {pair: 33, first: [6.7747, -0.2908, -2.4247], second: [5.8714, -0.0985, -2.2286], deltaE: 0.6377, branch: 'two near-blacks, L* under 10'},
];

/**
 * CIELAB (D65) of a few sRGB colours. White, black and mid grey are exact by construction — a neutral colour has a* =
 * b* = 0, and #808080 has L* 53.585 from the transfer function alone; the primaries are the values Lindbloom's reference
 * equations give, the ones colour libraries test their converters against.
 */
export const SRGB_LAB: ReadonlyArray<{hex: string; lab: Lab}> = [
    {hex: '#ffffff', lab: [100, 0, 0]},
    {hex: '#000000', lab: [0, 0, 0]},
    {hex: '#808080', lab: [53.585, 0, 0]},
    {hex: '#ff0000', lab: [53.2408, 80.0925, 67.2032]},
    {hex: '#0000ff', lab: [32.297, 79.1875, -107.8602]},
];

/**
 * Ottosson's "Table of example XYZ and Oklab pairs", provided with the definition to test implementations of it — B.
 * Ottosson, "A perceptual color space for image processing", 2020, https://bottosson.github.io/posts/oklab/ — the
 * OKLab of each XYZ rounded, as he writes it, to three decimals. The D65 white, then three imaginary colours that load
 * one axis each, so every coefficient of both matrices plays a part.
 */
export const OKLAB_XYZ: ReadonlyArray<{xyz: Xyz; oklab: Oklab}> = [
    {xyz: [0.95, 1, 1.089], oklab: [1, 0, 0]},
    {xyz: [1, 0, 0], oklab: [0.45, 1.236, -0.019]},
    {xyz: [0, 1, 0], oklab: [0.922, -0.671, 0.263]},
    {xyz: [0, 0, 1], oklab: [0.153, -1.415, -0.449]},
];

/**
 * sRGB colours in OKLCH as CSS Color Module Level 4 publishes them (W3C, §7 «HSL Colors: hsl() and hsla() functions»:
 * "In OkLCh, sRGB blue is oklch(0.452 0.313 264.1)…"), each at the digits the specification writes: the whole sRGB →
 * OKLCH chain, hue included. Two of them sit either side of the low edge of the green band the rule of the greens
 * reads, 115°: the yellow under it, the lime of `hsl(80deg 100% 50%)` in it. The two `hsl()` colours have exact
 * `#rrggbb` forms (`#0055ff`, 85 = 255/3; `#aaff00`, 170 = 2·255/3).
 */
export const SRGB_OKLCH: ReadonlyArray<{hex: string; what: string; oklch: string}> = [
    {hex: '#0000ff', what: 'sRGB blue', oklch: 'oklch(0.452 0.313 264.1)'},
    {hex: '#ffff00', what: 'sRGB yellow', oklch: 'oklch(0.968 0.211 109.8)'},
    {hex: '#0055ff', what: 'hsl(220deg 100% 50%)', oklch: 'oklch(0.533 0.26 262.6)'},
    {hex: '#aaff00', what: 'hsl(80deg 100% 50%)', oklch: 'oklch(0.91 0.245 129.9)'},
];
