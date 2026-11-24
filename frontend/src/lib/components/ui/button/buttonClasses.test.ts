/**
 * @vitest-environment node
 *
 * buttonClasses — the recipe of the standard button (project 85, BTN-0): one string of classes, colour roles only.
 *
 * - Every variant, size and shape returns role utilities only: no palette class (`text-gray-500`, `bg-white`), no
 *   `dark:` (a role changes value under `html.dark` by itself), no arbitrary colour.
 * - A toggle (`pressed`) replaces the variant's colours: one element never carries two colour utilities of one
 *   property in the same state (two plain `bg-…` would fight, the winner decided by the stylesheet's order).
 * - A link reads as text: no padding.
 * - `WORD_HIDDEN_BELOW` holds whole Tailwind classes written as literals in the source, since Tailwind finds a class
 *   only where it is written whole.
 *
 * The palette and role patterns come from the colour gates' own scanner (`scripts/theme/theme-roles.mjs`), so this
 * file and the gates agree on what a palette class is.
 */
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {describe, expect, it} from 'vitest';
import {ARBITRARY_VALUE_RE, LEGACY_CLASS_RE, ROLE_CLASS_RE} from '../../../../../scripts/theme/theme-roles.mjs';
import {buttonClasses, WORD_HIDDEN_BELOW, type ButtonSize, type ButtonVariant} from './buttonClasses';

const VARIANTS: ButtonVariant[] = ['primary', 'secondary', 'ghost', 'danger', 'danger-solid', 'warning', 'link'];
const SIZES: ButtonSize[] = ['sm', 'md', 'lg'];
const SHAPES = ['default', 'icon'] as const;
const PRESSED = [undefined, true, false] as const;

const COMBINATIONS = VARIANTS.flatMap((variant) => SIZES.flatMap((size) => SHAPES.flatMap((shape) => PRESSED.map((pressed) => ({variant, size, shape, pressed})))));

const tokens = (classes: string) => classes.split(/\s+/).filter(Boolean);
/** The colour utilities of a class string, as the colour gates read them (the patterns carry the `g` flag: `match`). */
const roleUtilities = (classes: string): string[] => [...(classes.match(ROLE_CLASS_RE) ?? [])];
/** A utility without variants (`bg-lf-card`, not `hover:bg-lf-hover`). */
const plain = (token: string) => !token.includes(':');

describe('buttonClasses — colour roles only', () => {
    it('barrier: the role pattern sees the roles of the default recipe', () => {
        expect(roleUtilities(buttonClasses()).length).toBeGreaterThan(1);
        expect('text-gray-500 bg-white'.match(LEGACY_CLASS_RE), 'the palette pattern must see a palette class').toHaveLength(2);
    });

    it.each(COMBINATIONS)('$variant $size $shape pressed=$pressed: no palette class, no dark:, no arbitrary colour', (options) => {
        const classes = buttonClasses(options);
        expect(classes.match(LEGACY_CLASS_RE) ?? []).toEqual([]);
        expect(tokens(classes).filter((token) => token.startsWith('dark:') || token.includes(':dark:'))).toEqual([]);
        expect(classes.match(ARBITRARY_VALUE_RE) ?? []).toEqual([]);
        expect(roleUtilities(classes).length, 'every combination draws its colours from the roles').toBeGreaterThan(0);
    });

    it.each(COMBINATIONS)('$variant $size $shape pressed=$pressed: one plain colour utility per property', (options) => {
        const plainTokens = tokens(buttonClasses(options)).filter(plain);
        for (const property of ['bg-lf-', 'text-lf-', 'border-lf-']) {
            const hits = plainTokens.filter((token) => token.startsWith(property));
            expect(hits.length, `${property}* without variants: ${hits.join(' ')}`).toBeLessThanOrEqual(1);
        }
    });
});

describe('buttonClasses — a toggle replaces the variant colours', () => {
    it.each(VARIANTS)('%s: pressed true and false carry the toggle colours, not the variant ones', (variant) => {
        const own = roleUtilities(buttonClasses({variant})).filter(plain);
        const on = buttonClasses({variant, pressed: true});
        const off = buttonClasses({variant, pressed: false});
        // Every variant carries the same toggle, whatever its own colours: the variant does not leak through.
        expect(on).toBe(buttonClasses({variant: 'secondary', pressed: true}));
        expect(off).toBe(buttonClasses({variant: 'secondary', pressed: false}));
        expect(on, 'on and off are drawn differently').not.toBe(off);
        // The variant's own colours are gone, unless the toggle happens to share them (the secondary's card).
        const shared = new Set(roleUtilities(on).concat(roleUtilities(off)));
        for (const token of own.filter((t) => !shared.has(t))) {
            expect(tokens(on)).not.toContain(token);
            expect(tokens(off)).not.toContain(token);
        }
    });
});

describe('buttonClasses — sizes', () => {
    const padding = (classes: string) => tokens(classes).filter((token) => /^p[xytrbl]?-/.test(token));

    it.each(SIZES)('a link of size %s has no padding, the others have some', (size) => {
        expect(padding(buttonClasses({variant: 'link', size}))).toEqual([]);
        expect(padding(buttonClasses({variant: 'primary', size})).length).toBeGreaterThan(0);
        expect(padding(buttonClasses({variant: 'ghost', size, shape: 'icon'})).length).toBeGreaterThan(0);
    });

    it('an icon button is square: one padding for both axes', () => {
        for (const size of SIZES) expect(padding(buttonClasses({size, shape: 'icon'})).every((token) => token.startsWith('p-'))).toBe(true);
    });
});

describe('WORD_HIDDEN_BELOW — literal Tailwind classes', () => {
    const source = readFileSync(fileURLToPath(new URL('./buttonClasses.ts', import.meta.url)), 'utf8');

    it.each(Object.entries(WORD_HIDDEN_BELOW))('%s → %s is a whole class written in the source', (threshold, cls) => {
        // `sm` → `max-sm:hidden`, `@2xl` → `@max-2xl:hidden`: Tailwind's own variant names, nothing assembled.
        const expected = threshold.startsWith('@') ? `@max-${threshold.slice(1)}:hidden` : `max-${threshold}:hidden`;
        expect(cls).toBe(expected);
        expect(source.includes(`'${cls}'`), `«${cls}» must appear quoted whole in buttonClasses.ts, or Tailwind never generates it`).toBe(true);
    });
});
