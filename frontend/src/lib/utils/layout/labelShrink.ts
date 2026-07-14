/**
 * labelShrink.ts — shared "shrink to fit" mechanism for text labels that would otherwise wrap
 * onto a second line (Tab labels in TabBar.svelte, Action button labels in PageToolbar.svelte).
 *
 * Some languages render the same UI string much longer than others (e.g. FR "Vue d'ensemble" vs
 * IT "Panoramica") — hiding the label outright as soon as it doesn't fit is wasteful; this module
 * instead computes, from REAL measured geometry, a single LINEAR scale factor (a continuous
 * ratio, not a handful of fixed discrete steps) and shrinks every label in a group UNIFORMLY, so
 * they keep matching sizes. `labelHideActions`/`labelHideTabs` (separate, per-page, user-tunable
 * width thresholds — see responsiveLayout.svelte.ts) remain the ONLY thing that ever makes a
 * label disappear entirely; this module only ever resizes, never hides.
 *
 * Framework-agnostic on purpose (plain DOM APIs, no Svelte runes) — both TabBar.svelte and
 * PageToolbar.svelte call into it, but "what counts as the available width for this label" means
 * something different for each (a Tab's own slot vs an Action button's content box minus its
 * icon), so that part stays with the caller; this module only turns (available, natural) pairs
 * into one shared scale and applies it.
 */

const NATURAL_FONT_SIZE_ATTR = 'lfNaturalFontSizePx';
/** How far the scale is allowed to shrink before giving up (1 = full size, this = the floor). */
export const DEFAULT_LABEL_SHRINK_FLOOR = 0.75;
/** Small bounded-retry safety net (see applyLinearShrink) for measurement-margin edge cases —
 *  mirrors the same bounded-retry philosophy already used by DateRangePicker's verifyNoWrap,
 *  but synchronous here (plain DOM style mutation, not a Svelte re-render to wait for). */
const MAX_VERIFY_ATTEMPTS = 3;
const VERIFY_STEP = 0.05;

/**
 * Reads and caches (on the element's own dataset) its ORIGINAL, unscaled font-size in px — the
 * stable reference point for every future scale computation. Idempotent: safe to call on every
 * pass, only ever reads `getComputedStyle` the very first time for a given element (subsequent
 * calls return the cached value even if an inline override is currently applied).
 */
export function captureNaturalFontSizePx(el: HTMLElement): number {
    const cached = el.dataset[NATURAL_FONT_SIZE_ATTR];
    if (cached) return parseFloat(cached);
    const natural = parseFloat(getComputedStyle(el).fontSize);
    el.dataset[NATURAL_FONT_SIZE_ATTR] = String(natural);
    return natural;
}

/**
 * Measures the natural (single-line, never-wrapped) width `el`'s CURRENT text content would
 * take at `naturalFontSizePx`, via an ephemeral offscreen clone — not a template-declared hidden
 * element (unlike DateRangePicker's static badge set, the labels shrunk here are dynamic/page-
 * provided, so the clone has to be created and torn down on the fly, same "measure reality"
 * spirit, just applied to an arbitrary runtime element instead of a fixed known set).
 */
export function measureNaturalWidth(el: HTMLElement, naturalFontSizePx: number): number {
    const clone = el.cloneNode(true) as HTMLElement;
    clone.style.position = 'absolute';
    clone.style.visibility = 'hidden';
    clone.style.pointerEvents = 'none';
    clone.style.whiteSpace = 'nowrap';
    clone.style.left = '-9999px';
    clone.style.top = '-9999px';
    clone.style.fontSize = `${naturalFontSizePx}px`;
    document.body.appendChild(clone);
    const width = clone.getBoundingClientRect().width;
    document.body.removeChild(clone);
    return width;
}

/**
 * True when `el`'s rendered box spans more than one line — compares real rendered height
 * against the single-line height implied by its own line-height, same "measure real geometry,
 * don't guess from character counts" principle as DateRangePicker's `anyRowWrapped`.
 */
export function isWrapped(el: HTMLElement): boolean {
    const cs = getComputedStyle(el);
    const lineHeight = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2;
    return el.getBoundingClientRect().height > lineHeight * 1.4; // tolerance margin
}

/**
 * Content-box width of `el` (excludes padding — `clientWidth` already excludes border for the
 * `border-box` sizing used throughout this codebase, but still INCLUDES padding, so that's
 * subtracted here to get the true inner width available to `el`'s children).
 */
export function innerContentWidth(el: HTMLElement): number {
    const cs = getComputedStyle(el);
    return el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
}

export interface ShrinkTarget {
    /** The label element itself — its `style.fontSize` is what gets adjusted. */
    label: HTMLElement;
    /** Width available to THIS label, in px — computed by the caller from stable DOM geometry
     *  (e.g. button/tab width minus icon/gap/padding). Must NOT be derived from the label's own
     *  current (possibly already-shrunk or currently-wrapped) box — it needs to stay valid
     *  regardless of the CURRENT scale, so the mechanism can grow back just as reliably as it
     *  shrinks (e.g. after a locale switch back to a shorter language, or a wider resize). */
    availableWidth: number;
}

/**
 * One measure→compute→apply pass over a group of labels that must shrink/grow UNIFORMLY (same
 * scale for every label in the group, so mixed-length text still reads as one consistent set —
 * e.g. all 3 Tab labels, or all N Action labels).
 *
 * The scale itself is a direct, continuous ratio — `min(1, available / natural)` per label,
 * the group takes the WORST (smallest) one, clamped to `floor` — a genuine linear scale derived
 * from measurement, not a choice between a few fixed discrete levels. Applied in ABSOLUTE px
 * (derived from each label's own natural size), never `em` — `em` is relative to the PARENT's
 * computed font-size, which would silently fight any Tailwind `text-*` class already on the
 * label and produce the wrong absolute size.
 *
 * Returns the applied scale (1 = untouched, `floor` = as small as allowed).
 */
export function applyLinearShrink(targets: ShrinkTarget[], floor: number = DEFAULT_LABEL_SHRINK_FLOOR): number {
    if (targets.length === 0) return 1;

    const measured = targets.map(({label, availableWidth}) => {
        const naturalPx = captureNaturalFontSizePx(label);
        const naturalWidth = measureNaturalWidth(label, naturalPx);
        const ratio = naturalWidth <= 0 ? 1 : availableWidth / naturalWidth;
        return {label, naturalPx, ratio};
    });

    let scale = Math.max(floor, Math.min(1, Math.min(...measured.map((m) => m.ratio))));
    applyScale(measured, scale);

    // Safety net: measurement margin (subpixel rounding, gap/padding read slightly off) can
    // rarely leave a label JUST barely wrapped despite the computed scale — nudge down a little
    // further and recheck, bounded, instead of trusting the first estimate blindly.
    for (let attempt = 0; attempt < MAX_VERIFY_ATTEMPTS && scale > floor; attempt++) {
        if (!measured.some(({label}) => isWrapped(label))) break;
        scale = Math.max(floor, scale - VERIFY_STEP);
        applyScale(measured, scale);
    }

    return scale;
}

function applyScale(measured: {label: HTMLElement; naturalPx: number}[], scale: number): void {
    for (const {label, naturalPx} of measured) {
        label.style.fontSize = scale >= 1 ? '' : `${naturalPx * scale}px`;
    }
}
