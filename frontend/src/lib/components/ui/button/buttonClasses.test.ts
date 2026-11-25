/**
 * @vitest-environment node
 *
 * buttonClasses — the recipe of the standard button (project 85, BTN-0 and BTN-2·0): one string of classes, colour
 * roles only.
 *
 * - Every combination of variant, size, shape, pressed, tone, tint and segment returns role utilities only: no palette
 *   class (`text-gray-500`, `bg-white`), no `dark:` (a role changes value under `html.dark` by itself), no arbitrary
 *   colour; one element never carries two plain colour utilities of one property (they would fight, the winner decided
 *   by the stylesheet's order); every hover is guarded (`not-disabled:not-aria-disabled:hover:`), so a button off or
 *   busy never lights up. A chip without a tone throws.
 * - The options of BTN-2·0 (C1–C11): `tone` (ghost, chip, pressed), `tint` wins over every other colour, `segment`
 *   (a ButtonGroup's member), the bar variants (the green sidebar's focus), `truncate`, `pill`, `dense`, the size `xs`.
 * - A toggle (`pressed`) replaces the variant's colours; a link has no padding and the small radius.
 * - `WORD_HIDDEN_BELOW` holds whole Tailwind classes written as literals in the source.
 *
 * The palette and role patterns come from the colour gates' own scanner (`scripts/theme/theme-roles.mjs`), and the
 * state colours from `lib/theme/toneClasses.ts`, so this file, the gates and the tone table agree.
 */
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {describe, expect, it} from 'vitest';
import {ARBITRARY_VALUE_RE, LEGACY_CLASS_RE, ROLE_CLASS_RE} from '../../../../../scripts/theme/theme-roles.mjs';
import {BUTTON_TONES, STATUS_TONES} from '$lib/theme/toneClasses';
import {buttonClasses, ICON_PX, WORD_HIDDEN_BELOW, type ButtonClassOptions, type ButtonSize, type ButtonTone, type ButtonVariant} from './buttonClasses';

const VARIANTS: ButtonVariant[] = ['primary', 'secondary', 'ghost', 'ghost-strong', 'danger', 'danger-solid', 'warning', 'link', 'link-muted', 'chip', 'bar-ghost', 'bar-solid', 'bar-link'];
const SIZES: ButtonSize[] = ['xs', 'sm', 'md', 'lg'];
const SHAPES = ['default', 'icon'] as const;
const PRESSED = [undefined, true, false] as const;
const TONES: ButtonTone[] = ['success', 'warning', 'danger', 'info'];
const GUARD = 'not-disabled:not-aria-disabled:hover:';

const tokens = (classes: string) => classes.split(/\s+/).filter(Boolean);
/** The colour utilities of a class string, as the colour gates read them (the patterns carry the `g` flag: `match`). */
const roleUtilities = (classes: string): string[] => [...(classes.match(ROLE_CLASS_RE) ?? [])];
/** A utility without variants (`bg-lf-card`, not `hover:bg-lf-hover`). */
const plain = (token: string) => !token.includes(':');
/** The arbitrary values that are colours (`bg-[#123]`): a size such as `text-[11px]` is not one. */
const arbitraryColours = (classes: string): string[] => [...classes.matchAll(ARBITRARY_VALUE_RE)].filter((m) => /#|rgba?\(|hsla?\(|oklch|oklab|color-mix|var\(--(?!lf-)/.test(m[1])).map((m) => m[0]);

/** Whether this combination must throw: a chip whose colour is its own (no pressed, tint or segment) and has no tone. */
const throwsWithoutTone = (o: ButtonClassOptions) => o.variant === 'chip' && !o.tone && o.pressed === undefined && !o.tint && !o.segment;

function* combinations(): Generator<ButtonClassOptions> {
    for (const variant of VARIANTS)
        for (const size of SIZES) for (const shape of SHAPES) for (const pressed of PRESSED) for (const tone of [undefined, ...TONES]) for (const tint of [undefined, 'warning'] as const) for (const segment of [false, true]) yield {variant, size, shape, pressed, tone, tint, segment};
}

/** Every rule a combination must keep; the broken ones, described, for a red that says which. */
function brokenRules(options: ButtonClassOptions): string[] {
    const classes = buttonClasses(options);
    const all = tokens(classes);
    const broken: string[] = [];
    if (classes.match(LEGACY_CLASS_RE)) broken.push(`palette ${classes.match(LEGACY_CLASS_RE)!.join(' ')}`);
    if (all.some((t) => t.startsWith('dark:') || t.includes(':dark:'))) broken.push('dark:');
    if (arbitraryColours(classes).length > 0) broken.push(`arbitrary colour ${arbitraryColours(classes).join(' ')}`);
    if (roleUtilities(classes).length === 0) broken.push('no role');
    for (const property of ['bg-lf-', 'text-lf-', 'border-lf-']) {
        const hits = all.filter(plain).filter((t) => t.startsWith(property));
        if (hits.length > 1) broken.push(`two ${property}*: ${hits.join(' ')}`);
    }
    const unguarded = all.filter((t) => t.includes('hover:') && !t.startsWith(GUARD));
    if (unguarded.length > 0) broken.push(`unguarded hover ${unguarded.join(' ')}`);
    if (all.some((t) => t.startsWith('enabled:'))) broken.push('enabled: (never matches an <a>)');
    return broken;
}

describe('buttonClasses — colour roles only, in every combination', () => {
    it('barrier: the patterns see what they must', () => {
        expect(roleUtilities(buttonClasses()).length).toBeGreaterThan(1);
        expect('text-gray-500 bg-white'.match(LEGACY_CLASS_RE), 'the palette pattern must see a palette class').toHaveLength(2);
        expect(arbitraryColours('bg-[#123456] text-[11px]'), 'a colour is an arbitrary colour, a size is not').toEqual(['bg-[#123456]']);
    });

    it('no palette, no dark:, no arbitrary colour, one plain utility per colour property, every hover guarded', () => {
        const failures: string[] = [];
        let checked = 0;
        for (const options of combinations()) {
            if (throwsWithoutTone(options)) continue;
            const broken = brokenRules(options);
            checked += 1;
            if (broken.length > 0) failures.push(`${JSON.stringify(options)}: ${broken.join('; ')}`);
        }
        expect(checked, 'the matrix ran').toBeGreaterThan(4000);
        expect(failures.slice(0, 20), `${failures.length} combinations break a rule`).toEqual([]);
    });

    it.each([{pill: true}, {truncate: true}, {dense: true}, {inline: true}, {pill: true, truncate: true, dense: true}, {inline: true, truncate: true}])('the shape options keep the rules: %o', (shapeOptions) => {
        for (const variant of VARIANTS) {
            const options = {variant, tone: variant === 'chip' ? ('info' as const) : undefined, ...shapeOptions};
            expect(brokenRules(options), variant).toEqual([]);
        }
    });
});

describe('buttonClasses — tone, chip and tint (C4, C5)', () => {
    it('a chip without a tone throws', () => {
        expect(() => buttonClasses({variant: 'chip'})).toThrow(/tone/);
    });

    it.each(TONES)('chip + %s: a border and the banner chip’s literals', (tone) => {
        const classes = tokens(buttonClasses({variant: 'chip', tone}));
        expect(classes).toContain('border');
        for (const literal of tokens(`${STATUS_TONES.bannerChip[tone].base} ${STATUS_TONES.bannerChip[tone].hover}`)) expect(classes).toContain(literal);
    });

    it.each(TONES)('ghost + %s is BUTTON_TONES.ghost', (tone) => {
        const classes = tokens(buttonClasses({variant: 'ghost', tone}));
        for (const literal of tokens(BUTTON_TONES.ghost[tone])) expect(classes).toContain(literal);
        expect(classes, 'the plain ghost colours are replaced').not.toContain('text-lf-muted');
    });

    it('variant danger is ghost + tone danger', () => {
        expect(buttonClasses({variant: 'danger'})).toBe(buttonClasses({variant: 'ghost', tone: 'danger'}));
    });

    it.each(TONES)('pressed + %s fills with the state; pressed with no tone is the checked control', (tone) => {
        const classes = tokens(buttonClasses({pressed: true, tone}));
        for (const literal of tokens(BUTTON_TONES.pressed[tone])) expect(classes).toContain(literal);
        expect(tokens(buttonClasses({pressed: true}))).toContain('bg-lf-checked');
    });

    it.each(TONES)('tint %s wins over the variant, pressed and segment', (tint) => {
        const expected = tokens(BUTTON_TONES.tint[tint]);
        for (const options of [{variant: 'primary' as const}, {variant: 'chip' as const, tone: 'info' as const}, {pressed: true}, {pressed: false}, {segment: true, pressed: true}, {variant: 'ghost' as const, tone: 'danger' as const}]) {
            const classes = tokens(buttonClasses({...options, tint}));
            for (const literal of expected) expect(classes, JSON.stringify(options)).toContain(literal);
            const colourRoles = roleUtilities(classes.join(' ')).filter((t) => !t.includes('outline-lf-'));
            expect(
                colourRoles.every((t) => expected.includes(t)),
                `${JSON.stringify(options)}: only the tint's colours, got ${colourRoles.join(' ')}`,
            ).toBe(true);
        }
    });
});

describe('buttonClasses — segment, bar, shape options (C1, C2, C3, C7, C9)', () => {
    it('a segment: rounded-none, lf-btn-segment, the focus inside, no border; the presets’ colours on and off', () => {
        for (const pressed of [true, false, undefined]) {
            const classes = tokens(buttonClasses({segment: true, pressed}));
            expect(classes).toEqual(expect.arrayContaining(['rounded-none', 'lf-btn-segment', 'focus-visible:-outline-offset-2', 'lf-btn-inset']));
            expect(classes).not.toContain('border');
            expect(classes).not.toContain('rounded-lg');
            expect(classes).not.toContain('focus-visible:outline-offset-2');
        }
        expect(tokens(buttonClasses({segment: true, pressed: true}))).toEqual(expect.arrayContaining(['bg-lf-checked', 'text-lf-on-checked']));
        expect(tokens(buttonClasses({segment: true, pressed: false}))).toEqual(expect.arrayContaining(['bg-lf-panel', 'text-lf-secondary', `${GUARD}bg-lf-neutral`]));
    });

    it.each(['bar-ghost', 'bar-solid', 'bar-link'] as const)('%s carries the bar’s focus (outline-lf-bar-focus, inside) and lf-btn-bar', (variant) => {
        const classes = tokens(buttonClasses({variant}));
        expect(classes).toEqual(expect.arrayContaining(['lf-btn-bar', 'lf-btn-inset', 'focus-visible:outline-lf-bar-focus', 'focus-visible:-outline-offset-2']));
        expect(classes).not.toContain('focus-visible:outline-lf-focus');
    });

    it('a page button carries the page’s focus, outside', () => {
        const classes = tokens(buttonClasses());
        expect(classes).toEqual(expect.arrayContaining(['focus-visible:outline-lf-focus', 'focus-visible:outline-offset-2']));
        expect(classes).not.toContain('lf-btn-bar');
    });

    it('truncate: min-w-0 and no shrink-0; without it, shrink-0', () => {
        expect(tokens(buttonClasses({truncate: true}))).toContain('min-w-0');
        expect(tokens(buttonClasses({truncate: true}))).not.toContain('shrink-0');
        expect(tokens(buttonClasses())).toContain('shrink-0');
        expect(tokens(buttonClasses())).not.toContain('min-w-0');
    });

    it('inline (C12): a hair of padding, the small radius, the 24 px target, and the line’s own text size', () => {
        for (const size of SIZES) {
            for (const shape of SHAPES) {
                const classes = tokens(buttonClasses({variant: 'link-muted', size, shape, inline: true}));
                expect(classes).toEqual(expect.arrayContaining(['gap-1', 'p-0.5', 'rounded', 'lf-btn-dense']));
                expect(
                    classes.filter((t) => /^text-(xs|sm|base|lg|\[)/.test(t)),
                    `${size} ${shape}: no text size of its own`,
                ).toEqual([]);
                expect(
                    classes.filter((t) => /^p[xytrbl]?-/.test(t)),
                    'only the hair of padding',
                ).toEqual(['p-0.5']);
                expect(classes).not.toContain('rounded-lg');
            }
        }
    });

    it('link-muted (C12): muted at rest, the link’s colour on a guarded hover', () => {
        const classes = tokens(buttonClasses({variant: 'link-muted'}));
        expect(classes).toContain('text-lf-muted');
        expect(classes).toContain(`${GUARD}text-lf-link`);
        expect(classes.filter((t) => t.startsWith('text-lf-') && !t.includes(':'))).toEqual(['text-lf-muted']);
    });

    it('ghost-strong (C13): the secondary text of the header and of every ghost that is secondary today, no fill', () => {
        const classes = tokens(buttonClasses({variant: 'ghost-strong'}));
        expect(classes.filter((t) => t.startsWith('text-lf-') && !t.includes(':'))).toEqual(['text-lf-secondary']);
        expect(classes).toContain(`${GUARD}bg-lf-hover`);
        expect(classes).toContain(`${GUARD}text-lf-primary`);
        expect(classes.filter((t) => (t.startsWith('bg-') || t.startsWith('border')) && !t.includes(':'))).toEqual([]);
        // The control: plain ghost stays muted.
        expect(tokens(buttonClasses({variant: 'ghost'})).filter((t) => t.startsWith('text-lf-') && !t.includes(':'))).toEqual(['text-lf-muted']);
    });

    it('an icon button keeps a gap between its icon and a badge or a chevron', () => {
        for (const size of SIZES)
            expect(
                tokens(buttonClasses({size, shape: 'icon'})).some((t) => t.startsWith('gap-')),
                size,
            ).toBe(true);
    });

    it('pill → rounded-full; dense → lf-btn-dense; xs → text-[11px] and a 12 px icon', () => {
        expect(tokens(buttonClasses({pill: true}))).toContain('rounded-full');
        expect(tokens(buttonClasses({pill: true}))).not.toContain('rounded-lg');
        expect(tokens(buttonClasses({dense: true}))).toContain('lf-btn-dense');
        expect(tokens(buttonClasses())).not.toContain('lf-btn-dense');
        expect(tokens(buttonClasses({size: 'xs'}))).toContain('text-[11px]');
        expect(tokens(buttonClasses({size: 'xs', shape: 'icon'}))).toContain('p-1');
        expect(ICON_PX.xs).toBe(12);
    });
});

describe('buttonClasses — a toggle replaces the variant colours', () => {
    const PLAIN_VARIANTS: ButtonVariant[] = ['primary', 'secondary', 'ghost', 'ghost-strong', 'danger', 'danger-solid', 'warning', 'link', 'link-muted'];

    it.each(PLAIN_VARIANTS)('%s: pressed true and false carry the toggle colours, not the variant ones', (variant) => {
        const own = roleUtilities(buttonClasses({variant})).filter(plain);
        const on = buttonClasses({variant, pressed: true});
        const off = buttonClasses({variant, pressed: false});
        // Every page variant carries the same toggle, whatever its own colours: the variant does not leak through.
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

    it.each(SIZES)('a link of size %s has no padding and the small radius; the others have padding', (size) => {
        for (const variant of ['link', 'bar-link'] as const) {
            expect(padding(buttonClasses({variant, size})), variant).toEqual([]);
            expect(tokens(buttonClasses({variant, size}))).toContain('rounded');
            expect(tokens(buttonClasses({variant, size}))).not.toContain('rounded-lg');
        }
        expect(padding(buttonClasses({variant: 'primary', size})).length).toBeGreaterThan(0);
        expect(padding(buttonClasses({variant: 'ghost', size, shape: 'icon'})).length).toBeGreaterThan(0);
        expect(tokens(buttonClasses({variant: 'primary', size}))).toContain('rounded-lg');
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
