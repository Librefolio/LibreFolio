/**
 * Color generation utilities using golden-ratio hue distribution.
 *
 * Provides consistent, visually distinct colors for dynamic lists
 * (broker badges, provider chips, priority badges, etc.).
 *
 * The golden angle (≈137.5°) ensures maximum hue separation between
 * consecutive indices, regardless of total count.
 */

/** Golden ratio conjugate — used for hue distribution */
const GOLDEN_RATIO = 0.618033988749895;

/** HSL color set for light and dark mode */
export interface ColorSet {
    bg: string;
    text: string;
    darkBg: string;
    darkText: string;
    /** Fully-saturated vivid color at the same hue — for dark row tints. */
    vivid: string;
    /** Medium-saturated pastel at the same hue — for light row tints. */
    vividLight: string;
}

/**
 * Generate a visually distinct color for a numeric index.
 *
 * Uses golden-ratio hue rotation starting from `startHue`.
 * Produces pleasant pastel backgrounds and readable text colors.
 *
 * @param index     0-based index (0 = first item)
 * @param startHue  Starting hue in degrees (default 140 = green)
 * @param opts      Optional overrides for saturation/lightness
 */
export function getIndexColor(
    index: number,
    startHue: number = 140,
    opts?: {
        saturation?: number;
        bgLightness?: number;
        textLightness?: number;
        darkBgLightness?: number;
        darkTextLightness?: number;
    },
): ColorSet {
    const sat = opts?.saturation ?? 35 + (index % 5) * 5; // 35-55%
    const bgL = opts?.bgLightness ?? 92;
    const txtL = opts?.textLightness ?? 30;
    const dBgL = opts?.darkBgLightness ?? 25;
    const dTxtL = opts?.darkTextLightness ?? 82;

    // Rotate hue by golden angle per index
    const hue = (startHue + index * GOLDEN_RATIO * 360) % 360;

    return {
        bg: `hsl(${hue}, ${sat}%, ${bgL}%)`,
        text: `hsl(${hue}, ${sat + 10}%, ${txtL}%)`,
        darkBg: `hsl(${hue}, ${sat}%, ${dBgL}%)`,
        darkText: `hsl(${hue}, ${sat + 10}%, ${dTxtL}%)`,
        vivid: `hsl(${hue}, 75%, 50%)`,
        vividLight: `hsl(${hue}, 60%, 80%)`,
    };
}

/**
 * Generate a semi-transparent background color for a provider code.
 *
 * Uses well-separated hues for known providers (ECB, FED, BOE, SNB)
 * and a spread hash for unknown ones. Colors are intentionally far
 * apart on the hue wheel for instant visual identification.
 *
 * @param code  Provider code (e.g. "ECB", "FED", "BOE", "SNB")
 * @returns     Object with bg/darkBg/border/darkBorder CSS colors
 */
export function getProviderColor(code: string): {bg: string; darkBg: string; border: string; darkBorder: string} {
    // Well-separated hue assignments for known providers (90° apart)
    const KNOWN_HUES: Record<string, number> = {
        ECB: 220, // Blue
        FED: 30, // Orange
        BOE: 150, // Teal/Green
        SNB: 340, // Magenta/Pink
        MANUAL: 0, // Red
    };

    let hue: number;
    if (code in KNOWN_HUES) {
        hue = KNOWN_HUES[code];
    } else {
        // Hash for unknown providers — large spread
        let hash = 0;
        for (let i = 0; i < code.length; i++) {
            hash = (hash * 127 + code.charCodeAt(i)) | 0;
        }
        hue = ((Math.abs(hash) * GOLDEN_RATIO) % 1) * 360;
    }

    const sat = 55;
    return {
        bg: `hsla(${hue}, ${sat}%, 50%, 0.12)`,
        darkBg: `hsla(${hue}, ${sat}%, 60%, 0.15)`,
        border: `hsla(${hue}, ${sat}%, 40%, 0.3)`,
        darkBorder: `hsla(${hue}, ${sat}%, 70%, 0.3)`,
    };
}

/**
 * Generate CSS style string for a priority badge.
 *
 * @param index  0-based priority index (0 = primary / #1)
 * @returns      Inline style string with CSS custom properties
 */
export function getPriorityBadgeStyle(index: number): string {
    const colors = getIndexColor(index, 140); // Start from green
    return `--badge-bg: ${colors.bg}; --badge-text: ${colors.text}; --badge-dark-bg: ${colors.darkBg}; --badge-dark-text: ${colors.darkText};`;
}

/**
 * Convert HSL (hue 0-360, saturation 0-100, lightness 0-100) to hex string (#rrggbb).
 *
 * Useful when a CSS hex color is needed (e.g. `<input type="color">`).
 */
export function hslToHex(h: number, s: number, l: number): string {
    s /= 100;
    l /= 100;
    const a = s * Math.min(l, 1 - l);
    const f = (n: number) => {
        const k = (n + h / 30) % 12;
        const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
        return Math.round(255 * color)
            .toString(16)
            .padStart(2, '0');
    };
    return `#${f(0)}${f(8)}${f(4)}`;
}

/**
 * Stable string hash → unsigned int. Used to fold an arbitrary string
 * (e.g. a tag name) into the same golden-ratio hue distribution used by
 * `getIndexColor()`.
 */
function hashString(s: string): number {
    let h = 5381;
    for (let i = 0; i < s.length; i++) {
        h = ((h << 5) + h + s.charCodeAt(i)) | 0; // djb2
    }
    // XOR-fold to spread similar-suffix strings apart
    h = ((h >>> 16) ^ h) | 0;
    return Math.abs(h);
}

/**
 * Resolve a deterministic `ColorSet` for an arbitrary string label
 * (tag, category, free-form chip). Same string → same color across
 * the app, with golden-ratio separation shared with broker / provider
 * / priority badges.
 *
 * @param label    String to colorize (case-insensitive)
 * @param startHue Starting hue in degrees (default 200 = cyan-blue)
 */
export function getStringColor(label: string, startHue: number = 200): ColorSet {
    if (!label) return getIndexColor(0, startHue);
    return getIndexColor(hashString(label), startHue);
}

/**
 * Inline-style snippet exposing CSS custom properties consumed by a
 * generic badge rule (`--badge-bg/--badge-text/--badge-dark-bg/--badge-dark-text`).
 * Pair with a CSS class that reads those variables.
 */
export function getStringBadgeStyle(label: string, startHue: number = 200): string {
    const c = getStringColor(label, startHue);
    return `--badge-bg:${c.bg};--badge-text:${c.text};--badge-dark-bg:${c.darkBg};--badge-dark-text:${c.darkText};`;
}
