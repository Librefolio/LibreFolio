/**
 * The ruler the colour tests measure with: CIEDE2000, the perceptual distance between two `#rrggbb` colours.
 *
 * A shared helper beside the other `$test` helpers, so the tests that judge whether two chart colours can be told apart
 * use one ruler, not a copy each. The formula is the one `allocationHierarchy.test.ts` and `allocationRings.test.ts`
 * wrote out (CIE 142-2001, kL = kC = kH = 1, as Sharma, Wu & Dalal (2005) write it), moved here unchanged.
 *
 * A ruler is proven before it measures anything: the published data it must reproduce is exported with it
 * (`SHARMA_PAIRS`, `SRGB_LAB`), and `src/lib/theme/chartCategories.test.ts` checks the ruler against it before its
 * distinguishability gate reads a single distance. A test that relies on this module and runs in another suite should
 * check it the same way: the data is here for that.
 *
 * Not a `*.test.ts`, so vitest does not collect it and `check-orphans` does not count it, and every `__tests__`
 * directory is outside coverage (`vitest.config.ts`).
 *
 * @module __tests__/colorDistance
 */

/** A colour in CIELAB, D65 white: `[L*, a*, b*]`. */
export type Lab = readonly [number, number, number];

/**
 * `#rrggbb` → CIELAB (D65): the sRGB transfer function (IEC 61966-2-1), the sRGB → XYZ matrix in its seven-digit form —
 * whose rows sum to the D65 white it divides by, so white lands on L* 100 with a* = b* = 0 — then CIE 1976 L*a*b* with
 * the exact ε = 216/24389 and κ = 24389/27.
 *
 * Throws on anything else: a ruler returning NaN compares false with every floor, and a pair measured with it would pass
 * in silence.
 */
export function labOf(hex: string): Lab {
    const match = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex);
    if (!match) throw new Error(`labOf: ${hex} is not #rrggbb`);
    const [r, g, b] = match.slice(1).map((channel) => {
        const c = parseInt(channel, 16) / 255;
        return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
    const x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b;
    const y = 0.2126729 * r + 0.7151522 * g + 0.072175 * b;
    const z = 0.0193339 * r + 0.119192 * g + 0.9503041 * b;
    const f = (t: number) => (t > 216 / 24389 ? Math.cbrt(t) : ((24389 / 27) * t + 16) / 116);
    const [fx, fy, fz] = [f(x / 0.95047), f(y), f(z / 1.08883)];
    return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
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
