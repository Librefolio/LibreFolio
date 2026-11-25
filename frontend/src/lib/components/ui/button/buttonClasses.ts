/**
 * The recipe of the standard button (project 85, BTN-0; the additions of BTN-2·0): one string of classes, colour roles
 * only.
 *
 * `Button.svelte` uses it, and so does whatever a component cannot reach: a button written as HTML inside a table
 * cell, a link that looks like a button (`<a>`), the hidden copies a picker measures. The behaviour (tap, long press,
 * name, disabled with a reason) is `pressable`; this file is only the look.
 *
 * Every class here is a literal: Tailwind finds a class only where it is written whole, and the colour gate reads the
 * same literals (`themeRoles.gate.test.ts`). Never assemble a class from pieces. The colours of the states live in
 * `lib/theme/toneClasses.ts` (`BUTTON_TONES`, `STATUS_TONES.bannerChip`) and are imported, never copied.
 *
 * - The hover colours apply only to a live button: `not-disabled:not-aria-disabled:hover:` — not natively disabled, not
 *   disabled with a reason, not busy.
 * - `class` on a button never corrects the base (`relative`, `shrink-0`, `whitespace-nowrap`, the focus): what changes
 *   the base is an option here (`truncate`, `segment`, `pill`, `dense`), and a position goes on a wrapper.
 * - `lf-btn` carries what classes cannot say (`button.css`): no callout and no text selection under a long press, the
 *   finger's target, the growing outline of a long press. `lf-btn-bar`, `lf-btn-inset`, `lf-btn-dense` and
 *   `lf-btn-segment` tell `button.css` the outline's colour and side and the target's size.
 */
import './button.css';
import {BUTTON_TONES, STATUS_TONES} from '$lib/theme/toneClasses';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'ghost-strong' | 'danger' | 'danger-solid' | 'warning' | 'link' | 'link-muted' | 'chip' | 'bar-ghost' | 'bar-solid' | 'bar-link';
export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg';
/** A state's colour: with `ghost` the button in that colour, with `chip` the chip of a banner, with `pressed` the fill. */
export type ButtonTone = 'success' | 'warning' | 'danger' | 'info';
/** What a button stands on (`tint`): a state's fill, or a fill of another colour whose text it inherits (`current`, C15). */
export type ButtonTint = ButtonTone | 'current';
/** `text`: the word; `icon-text`: icon and word; `icon`: the icon alone; `auto`: the word hides below a threshold. */
export type ButtonDisplay = 'text' | 'icon-text' | 'icon' | 'auto';
/**
 * Where the word of `display="auto"` hides. A viewport breakpoint (`sm`…`xl`: below it) or a container size
 * (`@xs`…`@4xl`: while the nearest `@container` ancestor is narrower; Tailwind's sizes, `@2xl` = 42rem).
 */
export type WordThreshold = 'sm' | 'md' | 'lg' | 'xl' | '@xs' | '@sm' | '@md' | '@lg' | '@xl' | '@2xl' | '@3xl' | '@4xl';

export interface ButtonClassOptions {
    variant?: ButtonVariant;
    size?: ButtonSize;
    /** `icon`: a square button holding only an icon. */
    shape?: 'default' | 'icon';
    /** A toggle (`aria-pressed`): `true` draws the selected control, `false` the idle one, whatever the variant. */
    pressed?: boolean;
    /** A state's colour (C4 + C5): `ghost` in that colour, the `chip` of a banner (mandatory there), the `pressed` fill. */
    tone?: ButtonTone;
    /** A button standing on a fill of that state (the ✕ of a toast or a banner): the fill's text, the hover a step down. */
    tint?: ButtonTint;
    /**
     * A segment (C2, C16): a filled toggle with no border — `panel` at rest, `neutral` on hover, `checked` pressed (a
     * `tone` wins when pressed) — and the focus inside. Alone it is `rounded-lg` (`rounded-full` with `pill`); `joined`
     * (inside a `ButtonGroup`) it has no radius and its finger target grows in height only.
     */
    segment?: boolean;
    /** The segment stands joined to its neighbours in a `ButtonGroup`: no radius, the target grows in height only. */
    joined?: boolean;
    /** One step less vertical padding (C16): `sm` → `py-1`, `md` → `py-1.5`; `xs`, `lg` and icons unchanged. */
    compact?: boolean;
    /** Fully rounded (C3): a pill. */
    pill?: boolean;
    /** The word may shrink and cut (C7): no `shrink-0`, `min-w-0`; the word takes `truncate`. */
    truncate?: boolean;
    /**
     * The word may break on lines (C17, a section head in a narrow dialog): no `shrink-0`, no nowrap, and — on `xs` only —
     * 14 px lines, so two of them fit in a 32 px row. No `min-w-0`: the button stays at least as wide as its longest word.
     * Never with `truncate`.
     */
    wrap?: boolean;
    /** Inside a field or beside a neighbour (C9): the finger's target is 24 px (WCAG 2.5.8), not 40. */
    dense?: boolean;
    /**
     * In a line of text (C12, the docs icon): `p-0.5` whatever the size, `rounded`, the 24 px target of `dense`; no text
     * size of its own — a word inherits the line's. `size` then chooses only the icon.
     */
    inline?: boolean;
    /**
     * A dashed edge (C14): the row that adds something or shows more («Add route», «Show 3 more»). Only on the variants
     * that have an edge, `secondary` and `chip`; elsewhere it changes nothing. Dashed means «add», never «off».
     */
    dashed?: boolean;
}

const BASE = 'lf-btn relative inline-flex items-center justify-center font-medium transition-colors cursor-pointer disabled:cursor-not-allowed disabled:opacity-50 aria-disabled:cursor-not-allowed aria-disabled:opacity-50 aria-busy:cursor-progress';

/** The focus outline (C1): the page's colour or the bar's, outside the button or inside it. */
const FOCUS = {
    page: 'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus',
    pageInset: 'lf-btn-inset focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-lf-focus',
    bar: 'lf-btn-bar lf-btn-inset focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-lf-bar-focus',
} as const;

/** The families of the inventory (`85_buttonStandard/notes/inventario-bottoni.md`, «Le ricette»), on the roles. */
const VARIANTS: Record<Exclude<ButtonVariant, 'chip'>, string> = {
    primary: 'bg-lf-action text-lf-on-action not-disabled:not-aria-disabled:hover:bg-lf-action-hover',
    secondary: 'border border-lf-input bg-lf-card text-lf-secondary not-disabled:not-aria-disabled:hover:bg-lf-hover not-disabled:not-aria-disabled:hover:text-lf-primary',
    ghost: 'text-lf-muted not-disabled:not-aria-disabled:hover:bg-lf-hover not-disabled:not-aria-disabled:hover:text-lf-secondary',
    /** The other half of the light buttons (C13): the secondary text — the header's controls (D-T23), and every ghost
     *  that is secondary today. A muted one stays `ghost`: the migration changes nothing in view. */
    'ghost-strong': 'text-lf-secondary not-disabled:not-aria-disabled:hover:bg-lf-hover not-disabled:not-aria-disabled:hover:text-lf-primary',
    /** The same literal as `ghost` with `tone="danger"`. */
    danger: BUTTON_TONES.ghost.danger,
    'danger-solid': 'bg-lf-danger-solid text-lf-on-danger-solid not-disabled:not-aria-disabled:hover:bg-lf-danger-hover',
    warning: 'bg-lf-warning text-lf-on-status not-disabled:not-aria-disabled:hover:bg-lf-warning-hover',
    link: 'text-lf-link not-disabled:not-aria-disabled:hover:underline',
    /** Grey at rest, the link's colour on hover: the sign that it opens the guide (C12, `DocsLink`). */
    'link-muted': 'text-lf-muted not-disabled:not-aria-disabled:hover:text-lf-link',
    /** The green sidebar (C1), its own roles: a ghost on the bar, the filled «log out», the muted link (the version). */
    'bar-ghost': 'text-lf-bar-text not-disabled:not-aria-disabled:hover:bg-lf-bar-hover',
    'bar-solid': 'bg-lf-bar-logout text-lf-bar-text not-disabled:not-aria-disabled:hover:bg-lf-bar-logout-hover',
    'bar-link': 'text-lf-bar-muted not-disabled:not-aria-disabled:hover:text-lf-bar-text',
};

/** A toggle replaces the variant's colours: two colour utilities of one property on one element would fight. */
const PRESSED_ON = 'border border-lf-checked bg-lf-checked text-lf-on-checked';
const PRESSED_OFF = 'border border-lf-input bg-lf-card text-lf-muted not-disabled:not-aria-disabled:hover:bg-lf-hover not-disabled:not-aria-disabled:hover:text-lf-secondary';

/** A segment (C2): the colours of today's presets, no border, so the width never moves when it is pressed. */
const SEGMENT_ON = 'bg-lf-checked text-lf-on-checked';
const SEGMENT_OFF = 'bg-lf-panel text-lf-secondary not-disabled:not-aria-disabled:hover:bg-lf-neutral';

/** Padding, gap and text size; the radius is apart (`pill`, `segment`). */
/** `compact` (C16): the same sizes one step lower — `text-xs py-1`, `text-sm py-1.5`, frequent in the app. */
const COMPACT_SIZES: Record<ButtonSize, string> = {
    xs: 'gap-1 px-2 py-0.5 text-[11px]',
    sm: 'gap-1 px-2.5 py-1 text-xs',
    md: 'gap-1.5 px-3 py-1.5 text-sm',
    lg: 'w-full gap-2 px-4 py-2.5 text-sm',
};

const SIZES: Record<ButtonSize, string> = {
    xs: 'gap-1 px-2 py-0.5 text-[11px]',
    sm: 'gap-1 px-2.5 py-1.5 text-xs',
    md: 'gap-1.5 px-3 py-2 text-sm',
    lg: 'w-full gap-2 px-4 py-2.5 text-sm',
};

/** The gap keeps a ▾ (`menu`, `expanded`) apart from the icon; a lone icon is untouched by it. */
const ICON_SIZES: Record<ButtonSize, string> = {
    xs: 'gap-0.5 p-1 text-[11px]',
    sm: 'gap-1 p-1.5 text-xs',
    md: 'gap-1 p-2 text-sm',
    lg: 'gap-1 p-2.5 text-sm',
};

/** A link reads as text: no padding, its size only. */
const LINK_SIZES: Record<ButtonSize, string> = {
    xs: 'gap-1 text-[11px]',
    sm: 'gap-1 text-xs',
    md: 'gap-1.5 text-sm',
    lg: 'gap-2 text-sm',
};

/** In a line of text (C12): a hair of padding, no text size — the word takes the line's. */
const INLINE_BOX = 'gap-1 p-0.5';

/** The class that hides the word of `display="auto"` below its threshold. */
export const WORD_HIDDEN_BELOW: Record<WordThreshold, string> = {
    sm: 'max-sm:hidden',
    md: 'max-md:hidden',
    lg: 'max-lg:hidden',
    xl: 'max-xl:hidden',
    '@xs': '@max-xs:hidden',
    '@sm': '@max-sm:hidden',
    '@md': '@max-md:hidden',
    '@lg': '@max-lg:hidden',
    '@xl': '@max-xl:hidden',
    '@2xl': '@max-2xl:hidden',
    '@3xl': '@max-3xl:hidden',
    '@4xl': '@max-4xl:hidden',
};

/** The icon's size in px for each button size (lucide's `size`). */
export const ICON_PX: Record<ButtonSize, number> = {xs: 12, sm: 14, md: 16, lg: 18};

function isBar(variant: ButtonVariant): boolean {
    return variant === 'bar-ghost' || variant === 'bar-solid' || variant === 'bar-link';
}

function isLink(variant: ButtonVariant): boolean {
    return variant === 'link' || variant === 'bar-link';
}

function colours({variant = 'secondary', pressed, tone, tint, segment}: ButtonClassOptions): string {
    if (tint) return BUTTON_TONES.tint[tint];
    if (segment) return pressed ? (tone ? BUTTON_TONES.segmentPressed[tone] : SEGMENT_ON) : SEGMENT_OFF;
    if (pressed !== undefined) {
        if (!pressed) return PRESSED_OFF;
        return tone ? BUTTON_TONES.pressed[tone] : PRESSED_ON;
    }
    if (variant === 'chip') {
        if (!tone) throw new Error('buttonClasses: a chip needs a tone (success, warning, danger or info)');
        return `border ${STATUS_TONES.bannerChip[tone].base} ${STATUS_TONES.bannerChip[tone].hover}`;
    }
    if (variant === 'ghost' && tone) return BUTTON_TONES.ghost[tone];
    return VARIANTS[variant];
}

/** The classes of a standard button. */
export function buttonClasses(options: ButtonClassOptions = {}): string {
    const {variant = 'secondary', size = 'md', shape = 'default', pressed, segment = false, joined = false, compact = false, pill = false, truncate = false, dense = false, inline = false, dashed = false, wrap = false} = options;
    const link = isLink(variant) && pressed === undefined && !segment;
    const box = inline ? INLINE_BOX : link ? LINK_SIZES[size] : shape === 'icon' ? ICON_SIZES[size] : compact ? COMPACT_SIZES[size] : SIZES[size];
    const radius = segment && joined ? 'rounded-none' : pill ? 'rounded-full' : link || inline ? 'rounded' : 'rounded-lg';
    const focus = isBar(variant) ? FOCUS.bar : segment ? FOCUS.pageInset : FOCUS.page;
    const flex = truncate ? 'min-w-0 whitespace-nowrap' : wrap ? (size === 'xs' ? 'whitespace-normal leading-3.5' : 'whitespace-normal') : 'shrink-0 whitespace-nowrap';
    const marks = [segment && joined ? 'lf-btn-segment' : '', dense || inline ? 'lf-btn-dense' : ''].filter(Boolean).join(' ');
    const edged = !options.tint && !segment && pressed === undefined && (variant === 'secondary' || variant === 'chip');
    const edge = dashed && edged ? 'border-dashed' : '';
    return [BASE, flex, focus, box, radius, colours(options), edge, marks].filter(Boolean).join(' ');
}
