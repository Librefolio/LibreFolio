/**
 * The recipe of the standard button (project 85, BTN-0): one string of classes, colour roles only.
 *
 * `Button.svelte` uses it, and so does whatever a component cannot reach: a button written as HTML inside a table
 * cell, a link that looks like a button (`<a>`). The behaviour (tap, long press, name, disabled with a reason) is
 * `pressable`; this file is only the look.
 *
 * Every class here is a literal: Tailwind finds a class only where it is written whole, and the colour gate reads the
 * same literals (`themeRoles.gate.test.ts`). Never assemble a class from pieces.
 *
 * - The hover colours apply only to a live button: `not-disabled:not-aria-disabled:hover:` — not natively disabled, not
 *   disabled with a reason.
 * - `lf-btn` carries what classes cannot say (`button.css`): no callout and no text selection under a long press, the
 *   40 px target under a coarse pointer, the growing outline of a long press.
 */
import './button.css';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'danger-solid' | 'warning' | 'link';
export type ButtonSize = 'sm' | 'md' | 'lg';
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
}

const BASE =
    'lf-btn relative inline-flex shrink-0 items-center justify-center font-medium whitespace-nowrap transition-colors cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50 aria-disabled:cursor-not-allowed aria-disabled:opacity-50 aria-busy:cursor-progress';

/** The families of the inventory (`85_buttonStandard/notes/inventario-bottoni.md`, «Le ricette»), on the roles. */
const VARIANTS: Record<ButtonVariant, string> = {
    primary: 'bg-lf-action text-lf-on-action not-disabled:not-aria-disabled:hover:bg-lf-action-hover',
    secondary: 'border border-lf-input bg-lf-card text-lf-secondary not-disabled:not-aria-disabled:hover:bg-lf-hover not-disabled:not-aria-disabled:hover:text-lf-primary',
    ghost: 'text-lf-muted not-disabled:not-aria-disabled:hover:bg-lf-hover not-disabled:not-aria-disabled:hover:text-lf-secondary',
    danger: 'text-lf-danger not-disabled:not-aria-disabled:hover:bg-lf-danger-soft not-disabled:not-aria-disabled:hover:text-lf-danger-on-soft',
    'danger-solid': 'bg-lf-danger-solid text-lf-on-danger-solid not-disabled:not-aria-disabled:hover:bg-lf-danger-hover',
    warning: 'bg-lf-warning text-lf-on-status not-disabled:not-aria-disabled:hover:bg-lf-warning-hover',
    link: 'text-lf-link not-disabled:not-aria-disabled:hover:underline',
};

/** A toggle replaces the variant's colours: two colour utilities of one property on one element would fight. */
const PRESSED_ON = 'border border-lf-checked bg-lf-checked text-lf-on-checked';
const PRESSED_OFF = 'border border-lf-input bg-lf-card text-lf-muted not-disabled:not-aria-disabled:hover:bg-lf-hover not-disabled:not-aria-disabled:hover:text-lf-secondary';

const SIZES: Record<ButtonSize, string> = {
    sm: 'gap-1 rounded-lg px-2.5 py-1.5 text-xs',
    md: 'gap-1.5 rounded-lg px-3 py-2 text-sm',
    lg: 'w-full gap-2 rounded-lg px-4 py-2.5 text-sm',
};

const ICON_SIZES: Record<ButtonSize, string> = {
    sm: 'rounded-lg p-1.5 text-xs',
    md: 'rounded-lg p-2 text-sm',
    lg: 'rounded-lg p-2.5 text-sm',
};

/** A link reads as text: no padding, its size only. */
const LINK_SIZES: Record<ButtonSize, string> = {
    sm: 'gap-1 rounded text-xs',
    md: 'gap-1.5 rounded text-sm',
    lg: 'gap-2 rounded text-sm',
};

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
export const ICON_PX: Record<ButtonSize, number> = {sm: 14, md: 16, lg: 18};

/** The classes of a standard button. */
export function buttonClasses({variant = 'secondary', size = 'md', shape = 'default', pressed}: ButtonClassOptions = {}): string {
    const colours = pressed === undefined ? VARIANTS[variant] : pressed ? PRESSED_ON : PRESSED_OFF;
    const box = variant === 'link' && pressed === undefined ? LINK_SIZES[size] : shape === 'icon' ? ICON_SIZES[size] : SIZES[size];
    return `${BASE} ${box} ${colours}`;
}
