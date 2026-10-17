/**
 * Designer Lab — colour parsing, conversion and contrast.
 *
 * Debug-only tooling (see `design-designerLab.md`). Plain ESM JavaScript with JSDoc types on purpose: the
 * build-time scanner (`frontend/scripts/designer-lab/scan-colors.mjs`, run by Node and by the Vite plugin) and
 * the runtime engine (browser) import the same file, without a compile step in between.
 *
 * Colours are carried as `Rgba`: sRGB channels in 0..1 (they may fall outside 0..1 when the colour is outside the
 * sRGB gamut, e.g. a saturated `oklch()`), plus alpha in 0..1. OKLab/OKLCH use Björn Ottosson's matrices; display-p3
 * goes through CIE XYZ (D65).
 */

/** @typedef {{r: number, g: number, b: number, alpha: number}} Rgba */
/** @typedef {{l: number, c: number, h: number, alpha: number}} Oklch */

const HEX_RE = /^#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$/i;
const FN_RE = /^(rgba?|hsla?|oklch|oklab|color)\(\s*([^()]*)\)$/i;

/**
 * Every colour token a text can contain: hex literals and colour functions (one level of nested parentheses, as in
 * `rgb(calc(…))`). The look-behind keeps `&#123;` and identifiers such as `id#fff` out. Global: use with `matchAll`.
 */
export const COLOR_TOKEN_RE = /(?<![\w&#])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b|\b(?:rgba?|hsla?|oklch|oklab|color)\((?:[^()]|\([^()]*\))*\)/g;

const NAMED = /** @type {Record<string, [number, number, number, number]>} */ ({
    white: [255, 255, 255, 1],
    black: [0, 0, 0, 1],
    transparent: [0, 0, 0, 0],
});

/** @param {number} x @param {number} lo @param {number} hi */
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));

/**
 * A number or a percentage. `percentScale` is what 100% is worth (1 for alpha and sRGB channels, 0.4 for OKLCH
 * chroma). `none` reads as 0, as CSS Color 4 says for computation.
 * @param {string} token
 * @param {number} percentScale
 * @returns {number | null}
 */
function num(token, percentScale) {
    const t = token.trim().toLowerCase();
    if (t === 'none') return 0;
    if (t.endsWith('%')) {
        const v = Number(t.slice(0, -1));
        return Number.isFinite(v) ? (v / 100) * percentScale : null;
    }
    const v = Number(t);
    return Number.isFinite(v) ? v : null;
}

/**
 * A hue in degrees.
 * @param {string} token
 * @returns {number | null}
 */
function hue(token) {
    const t = token.trim().toLowerCase();
    if (t === 'none') return 0;
    const m = /^(-?[\d.]+(?:e-?\d+)?)(deg|turn|rad|grad)?$/.exec(t);
    if (!m) return null;
    const v = Number(m[1]);
    if (!Number.isFinite(v)) return null;
    const unit = m[2] ?? 'deg';
    const deg = unit === 'turn' ? v * 360 : unit === 'rad' ? (v * 180) / Math.PI : unit === 'grad' ? v * 0.9 : v;
    return ((deg % 360) + 360) % 360;
}

/**
 * Split the arguments of a colour function into its components and its alpha: both the legacy comma form
 * (`rgba(30, 41, 59, .95)`) and the modern space form (`oklch(63.7% .237 25 / 50%)`).
 * @param {string} body
 * @returns {{parts: string[], alpha: string | null} | null}
 */
function splitArgs(body) {
    if (/var\(|calc\(|env\(|attr\(/i.test(body)) return null;
    if (body.includes(',')) {
        const parts = body.split(',').map((p) => p.trim());
        if (parts.some((p) => p === '')) return null;
        return parts.length === 4 ? {parts: parts.slice(0, 3), alpha: parts[3]} : {parts, alpha: null};
    }
    const [main, alpha] = body.split('/');
    const parts = main.trim().split(/\s+/).filter(Boolean);
    return {parts, alpha: alpha === undefined ? null : alpha.trim()};
}

/** @param {number} c */
const srgbToLinear = (c) => {
    const a = Math.abs(c);
    return a <= 0.04045 ? c / 12.92 : Math.sign(c) * ((a + 0.055) / 1.055) ** 2.4;
};

/** @param {number} c */
const linearToSrgb = (c) => {
    const a = Math.abs(c);
    return a <= 0.0031308 ? c * 12.92 : Math.sign(c) * (1.055 * a ** (1 / 2.4) - 0.055);
};

/**
 * @param {number} r @param {number} g @param {number} b  linear sRGB
 * @returns {[number, number, number]} OKLab
 */
function linearSrgbToOklab(r, g, b) {
    const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s, 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s];
}

/**
 * @param {number} L @param {number} a @param {number} b  OKLab
 * @returns {[number, number, number]} linear sRGB
 */
function oklabToLinearSrgb(L, a, b) {
    const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
    const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
    const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
    return [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s, -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s];
}

/**
 * Linear display-p3 → linear sRGB, through CIE XYZ (D65).
 * @param {number} r @param {number} g @param {number} b
 * @returns {[number, number, number]}
 */
function linearP3ToLinearSrgb(r, g, b) {
    const x = 0.4865709486482162 * r + 0.26566769316909306 * g + 0.1982172852343625 * b;
    const y = 0.2289745640697488 * r + 0.6917385218365064 * g + 0.079286914093745 * b;
    const z = 0.04511338185890264 * g + 1.043944368900976 * b;
    return [3.2409699419045226 * x - 1.537383177570094 * y - 0.4986107602930034 * z, -0.9692436362808796 * x + 1.8759675015077202 * y + 0.04155505740717559 * z, 0.05563007969699366 * x - 0.20397695888897652 * y + 1.0569715142428786 * z];
}

/**
 * @param {number} l @param {number} c @param {number} h @param {number} alpha
 * @returns {Rgba}
 */
export function oklchToRgba(l, c, h, alpha = 1) {
    const rad = (h * Math.PI) / 180;
    const [r, g, b] = oklabToLinearSrgb(l, c * Math.cos(rad), c * Math.sin(rad));
    return {r: linearToSrgb(r), g: linearToSrgb(g), b: linearToSrgb(b), alpha};
}

/**
 * @param {Rgba} rgba
 * @returns {Oklch}
 */
export function rgbaToOklch(rgba) {
    const [L, a, b] = linearSrgbToOklab(srgbToLinear(rgba.r), srgbToLinear(rgba.g), srgbToLinear(rgba.b));
    const c = Math.hypot(a, b);
    const h = c < 1e-6 ? 0 : ((((Math.atan2(b, a) * 180) / Math.PI) % 360) + 360) % 360;
    return {l: L, c, h, alpha: rgba.alpha};
}

/**
 * @param {number} h @param {number} s @param {number} l  hue in degrees, saturation and lightness in 0..1
 * @returns {[number, number, number]}
 */
function hslToRgb(h, s, l) {
    /** @param {number} n */
    const f = (n) => {
        const k = (n + h / 30) % 12;
        return l - s * Math.min(l, 1 - l) * Math.max(-1, Math.min(k - 3, 9 - k, 1));
    };
    return [f(0), f(8), f(4)];
}

/**
 * Parse one CSS colour literal: hex (3, 4, 6, 8 digits), `rgb()`/`rgba()`, `hsl()`/`hsla()`, `oklch()`, `oklab()`,
 * `color(srgb|srgb-linear|display-p3 …)`, and the keywords `white`, `black`, `transparent`. Anything that is an
 * expression rather than a value — `var()`, `calc()`, `color-mix()` — gives `null`.
 * @param {string} input
 * @returns {Rgba | null}
 */
export function parseColor(input) {
    const text = input.trim().toLowerCase();
    const named = NAMED[text];
    if (named) return {r: named[0] / 255, g: named[1] / 255, b: named[2] / 255, alpha: named[3]};

    const hex = HEX_RE.exec(text);
    if (hex) {
        let digits = hex[1];
        if (digits.length <= 4) digits = [...digits].map((d) => d + d).join('');
        const byte = (/** @type {number} */ i) => parseInt(digits.slice(i, i + 2), 16) / 255;
        return {r: byte(0), g: byte(2), b: byte(4), alpha: digits.length === 8 ? byte(6) : 1};
    }

    const fn = FN_RE.exec(text);
    if (!fn) return null;
    const name = fn[1];
    const args = splitArgs(fn[2]);
    if (!args) return null;
    const alpha = args.alpha === null ? 1 : num(args.alpha, 1);
    if (alpha === null) return null;
    const a = clamp(alpha, 0, 1);
    const p = args.parts;

    if (name === 'rgb' || name === 'rgba') {
        if (p.length !== 3) return null;
        const ch = p.map((t) => num(t, 255));
        if (ch.some((v) => v === null)) return null;
        const [r, g, b] = /** @type {number[]} */ (ch);
        return {r: r / 255, g: g / 255, b: b / 255, alpha: a};
    }
    if (name === 'hsl' || name === 'hsla') {
        if (p.length !== 3) return null;
        const h = hue(p[0]);
        const s = num(p[1], 1);
        const l = num(p[2], 1);
        if (h === null || s === null || l === null) return null;
        // Modern syntax allows bare numbers for s and l on a 0..100 scale.
        const sat = p[1].includes('%') ? s : s / 100;
        const lig = p[2].includes('%') ? l : l / 100;
        const [r, g, b] = hslToRgb(h, clamp(sat, 0, 1), clamp(lig, 0, 1));
        return {r, g, b, alpha: a};
    }
    if (name === 'oklch') {
        if (p.length !== 3) return null;
        const l = num(p[0], 1);
        const c = num(p[1], 0.4);
        const h = hue(p[2]);
        if (l === null || c === null || h === null) return null;
        return oklchToRgba(l, Math.max(0, c), h, a);
    }
    if (name === 'oklab') {
        if (p.length !== 3) return null;
        const L = num(p[0], 1);
        const A = num(p[1], 0.4);
        const B = num(p[2], 0.4);
        if (L === null || A === null || B === null) return null;
        const [r, g, b] = oklabToLinearSrgb(L, A, B);
        return {r: linearToSrgb(r), g: linearToSrgb(g), b: linearToSrgb(b), alpha: a};
    }
    // color(<space> c1 c2 c3)
    if (p.length !== 4) return null;
    const space = p[0];
    const ch = p.slice(1).map((t) => num(t, 1));
    if (ch.some((v) => v === null)) return null;
    const [c1, c2, c3] = /** @type {number[]} */ (ch);
    if (space === 'srgb') return {r: c1, g: c2, b: c3, alpha: a};
    if (space === 'srgb-linear') return {r: linearToSrgb(c1), g: linearToSrgb(c2), b: linearToSrgb(c3), alpha: a};
    if (space === 'display-p3') {
        const [r, g, b] = linearP3ToLinearSrgb(srgbToLinear(c1), srgbToLinear(c2), srgbToLinear(c3));
        return {r: linearToSrgb(r), g: linearToSrgb(g), b: linearToSrgb(b), alpha: a};
    }
    return null;
}

/**
 * Whether the colour fits sRGB, with a tolerance of half an 8-bit step by default.
 * @param {Rgba} rgba
 * @param {number} [eps]
 */
export function inSrgbGamut(rgba, eps = 0.5 / 255) {
    return [rgba.r, rgba.g, rgba.b].every((v) => v >= -eps && v <= 1 + eps);
}

/**
 * The closest colour inside sRGB with the same OKLCH lightness and hue: chroma is reduced by bisection.
 * @param {Rgba} rgba
 * @returns {Rgba}
 */
export function clampToSrgb(rgba) {
    if (inSrgbGamut(rgba, 0)) return rgba;
    const {l, c, h, alpha} = rgbaToOklch(rgba);
    if (l >= 1) return {r: 1, g: 1, b: 1, alpha};
    if (l <= 0) return {r: 0, g: 0, b: 0, alpha};
    let lo = 0;
    let hi = c;
    for (let i = 0; i < 24; i++) {
        const mid = (lo + hi) / 2;
        if (inSrgbGamut(oklchToRgba(l, mid, h, alpha), 0)) lo = mid;
        else hi = mid;
    }
    const out = oklchToRgba(l, lo, h, alpha);
    return {r: clamp(out.r, 0, 1), g: clamp(out.g, 0, 1), b: clamp(out.b, 0, 1), alpha};
}

/** @param {number} v */
const byteHex = (v) =>
    Math.round(clamp(v, 0, 1) * 255)
        .toString(16)
        .padStart(2, '0');

/**
 * `#rrggbb`, or `#rrggbbaa` when the colour is not opaque (and `withAlpha` is not false). Out-of-gamut colours are
 * clamped to sRGB first.
 * @param {Rgba} rgba
 * @param {boolean} [withAlpha]
 */
export function toHex(rgba, withAlpha = true) {
    const c = clampToSrgb(rgba);
    const base = `#${byteHex(c.r)}${byteHex(c.g)}${byteHex(c.b)}`;
    return withAlpha && rgba.alpha < 1 ? base + byteHex(rgba.alpha) : base;
}

/** @param {number} v @param {number} digits */
const round = (v, digits) => {
    const f = 10 ** digits;
    return Math.round(v * f) / f;
};

/**
 * `oklch(L% C H)` in the notation Tailwind v4 writes, with `/ alpha` when not opaque.
 * @param {Oklch} o
 */
export function formatOklch(o) {
    const core = `oklch(${round(o.l * 100, 2)}% ${round(o.c, 4)} ${round(o.h, 2)})`;
    return o.alpha < 1 ? core.replace(')', ` / ${round(o.alpha, 3)})`) : core;
}

/**
 * A colour that canvas libraries can parse (ECharts' zrender reads hex, rgb() and hsl(), not oklch()): `rgba()` when
 * not opaque, else `#rrggbb`, clamped to sRGB.
 * @param {Rgba} rgba
 */
export function toCanvasColor(rgba) {
    const c = clampToSrgb(rgba);
    if (rgba.alpha >= 1) return toHex(c, false);
    return `rgba(${Math.round(c.r * 255)}, ${Math.round(c.g * 255)}, ${Math.round(c.b * 255)}, ${round(rgba.alpha, 3)})`;
}

/**
 * The key that groups equal colours regardless of how they are written: `#rrggbb` (opaque, lower case) when the
 * colour is inside sRGB, `oklch(…)` with fixed rounding when it is not. Alpha is NOT part of the key: alpha variants
 * of one colour share it.
 * @param {Rgba} rgba
 */
export function colorKey(rgba) {
    if (inSrgbGamut(rgba)) return toHex({...rgba, alpha: 1}, false);
    const o = rgbaToOklch(rgba);
    return `oklch(${round(o.l, 4)} ${round(o.c, 4)} ${round(o.h, 1)})`;
}

/**
 * WCAG 2 relative luminance (sRGB, clamped).
 * @param {Rgba} rgba
 */
export function relativeLuminance(rgba) {
    const c = clampToSrgb(rgba);
    const lin = [c.r, c.g, c.b].map((v) => srgbToLinear(clamp(v, 0, 1)));
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
}

/**
 * Composite `fg` over an opaque `bg` (alpha blending in sRGB, as browsers paint).
 * @param {Rgba} fg
 * @param {Rgba} bg
 * @returns {Rgba}
 */
export function composite(fg, bg) {
    const a = fg.alpha;
    return {r: fg.r * a + bg.r * (1 - a), g: fg.g * a + bg.g * (1 - a), b: fg.b * a + bg.b * (1 - a), alpha: 1};
}

/**
 * WCAG 2 contrast ratio of a foreground over a background; a translucent foreground is composited first.
 * @param {Rgba} fg
 * @param {Rgba} bg
 */
export function contrastRatio(fg, bg) {
    const solidBg = {...bg, alpha: 1};
    const f = relativeLuminance(fg.alpha < 1 ? composite(fg, solidBg) : fg);
    const b = relativeLuminance(solidBg);
    const [hi, lo] = f > b ? [f, b] : [b, f];
    return (hi + 0.05) / (lo + 0.05);
}

/**
 * Replace the colour tokens of a text. `map` receives each parsed token and returns the replacement text, or `null`
 * to keep it. Used for CSS values (L2) and for the strings and HTML an ECharts option carries (L3).
 * @param {string} text
 * @param {(rgba: Rgba, raw: string) => string | null} map
 * @returns {string}
 */
export function replaceColorTokens(text, map) {
    if (!text) return text;
    return text.replace(COLOR_TOKEN_RE, (raw) => {
        const rgba = parseColor(raw);
        if (!rgba) return raw;
        return map(rgba, raw) ?? raw;
    });
}
