/**
 * roleColors — the sRGB bridge from the roles of tokens.css to the charts (D-T5, DV), where there is no page: the
 * parity gate, and every path that reads no DOM.
 *
 * - **The parity gate.** Where tokens.css is not loaded — unit tests, server rendering — a role reads empty and a
 *   stand-in takes its place. `lib/theme/` is outside the colour ratchet, so nothing but this gate keeps the stand-ins
 *   equal to tokens.css: for every role the charts read, in both themes, the stand-in must be what the gate's own
 *   resolver (`scripts/theme/theme-roles.mjs`, as `src/themeTokens.gate.test.ts` uses it) makes of `var(<role>)` — the
 *   same `#rrggbb` for an opaque role; for a translucent one (`--lf-selected`), an `rgba(r,g,b,a)` with the resolver's
 *   channels at 8 bits and its alpha within 1e-3, in the comma form `toRgba` writes and zrender reads. Its red says
 *   what to do: «update the stand-in in roleColors.ts to tokens.css».
 * - **The role list is the module's.** `ChartRole` is a type, erased at run time, so the list is scraped from its
 *   declaration in roleColors.ts: a role added to the union enters the gate the day it is declared. The union is read
 *   on one line or as Prettier breaks it, one member per line after a leading `|`, and a member written otherwise is
 *   named, never skipped. Positive control: every role of the union is read by chart code — directly,
 *   `.color('--lf-…')` in a production source, or through `readableText`, whose reads are recorded at run time — so the
 *   gate checks no dead role. A role declared ahead of its reader waits in `PENDING_READERS`, named with the batch that
 *   will read it; the list only shrinks: once production code reads a role, a red asks that batch to remove its line.
 * - **The paths without a page.** An injected reader answers before any element is looked for, so it works here, and
 *   it is handed the scope; with none, a node run reads every stand-in. A `#rrggbb` passes as it is; any other notation
 *   needs a canvas, which a node run has not, so the stand-in takes its place. `dark` picks the stand-in, nothing else.
 *   `readableText` takes the primary text or the inverse one, measuring a translucent background over the card.
 *
 * The paths through a page — the computed style of `<html>` or of the scope, taken once per draw, and the canvas that
 * resolves any other notation — are `roleColors.dom.test.ts`'s (jsdom).
 *
 * Node env.
 *
 * @module lib/theme/roleColors.test
 */
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {afterEach, describe, expect, it, vi} from 'vitest';

import {listSources, readTokens, resolveColour, SRC_DIR, toHex} from '../../../scripts/theme/theme-roles.mjs';

import {parseRgba} from './colorAlpha';
import {chartRoles, type ChartRole, type RoleReader, setRoleReader} from './roleColors';

const ROLE_COLORS_TS = path.join(path.dirname(fileURLToPath(import.meta.url)), 'roleColors.ts');
const THEMES = ['light', 'dark'] as const;

/** At or above this alpha a colour is opaque (as `themeTokens.gate.test.ts` reads it: a mix sums its weights in floating point). */
const OPAQUE = 1 - 1e-9;

/**
 * Roles of ChartRole declared ahead of their reader, each with the batch that will read it: the dead-role check takes
 * them as read until then. The list only shrinks — once production code reads a role, the check of the pending roles
 * goes red until the reading batch removes its line.
 */
const PENDING_READERS: Readonly<Record<string, string>> = {};
const PENDING = new Set(Object.keys(PENDING_READERS));

afterEach(() => {
    setRoleReader(null);
});

/**
 * The members of the one `export type ChartRole = …;` in `source`, each a quoted role — or a marker naming a member
 * written otherwise. Pure, so the forms it must read are tried on synthetic sources too. One leading `|` is the
 * syntax's, not a member: Prettier writes it before the first member once the union no longer fits on one line.
 */
function scrapeChartRoles(source: string): {roles: ChartRole[]; declarations: number; unread: string[]} {
    const declarations = [...source.matchAll(/export type ChartRole\s*=([^;]+);/g)];
    if (declarations.length !== 1) return {roles: [], declarations: declarations.length, unread: []};
    const members = declarations[0][1]
        .trim()
        .replace(/^\|/, '')
        .split('|')
        .map((member) => member.trim());
    const roles = members.flatMap((member) => /^'(--lf-[a-z0-9-]+)'$/.exec(member)?.[1] ?? []) as ChartRole[];
    return {roles, declarations: 1, unread: members.filter((member) => !/^'--lf-[a-z0-9-]+'$/.test(member))};
}

const SCRAPE = scrapeChartRoles(readFileSync(ROLE_COLORS_TS, 'utf-8'));
const ROLES = SCRAPE.roles;
const ROLE_THEMES = ROLES.flatMap((role) => THEMES.map((theme) => [role, theme] as const));

/** Every role a production source reads directly, `.color('--lf-…')`, outside the bridge itself; and who calls readableText. */
function chartCodeReads(): {direct: Set<string>; readableTextCallers: string[]} {
    const direct = new Set<string>();
    const readableTextCallers: string[] = [];
    for (const rel of listSources()) {
        if (rel === 'lib/theme/roleColors.ts') continue;
        const text = readFileSync(path.join(SRC_DIR, rel), 'utf-8');
        for (const match of text.matchAll(/\.color\(\s*'(--lf-[a-z0-9-]+)'\s*\)/g)) direct.add(match[1]);
        if (/\.readableText\(/.test(text)) readableTextCallers.push(rel);
    }
    return {direct, readableTextCallers};
}

/** The roles `readableText` reads, recorded through an injected reader. */
function rolesReadByReadableText(): Set<string> {
    const asked = new Set<string>();
    setRoleReader((role) => {
        asked.add(role);
        return '';
    });
    chartRoles(false, null).readableText('#808080');
    setRoleReader(null);
    return asked;
}

describe('the role list — scraped from the ChartRole union, and every role read by chart code', () => {
    it('reads the union: one declaration, every member a quoted role, the roles certainly there among them', () => {
        expect(SCRAPE.declarations, 'roleColors.ts: expected exactly one `export type ChartRole = …;`').toBe(1);
        expect(SCRAPE.unread, 'members of ChartRole the scrape cannot read as a quoted role: the parity gate would skip them').toEqual([]);
        expect(ROLES).toEqual(expect.arrayContaining(['--lf-surface-card', '--lf-text-primary', '--lf-danger', '--lf-info']));
    });

    it('positive control: the scrape reads the union on one line and as Prettier breaks it, and still names a member it cannot read', () => {
        const roles = ['--lf-surface-card', '--lf-text-primary', '--lf-info'];
        const forms = {
            'one line': `export type ChartRole = ${roles.map((role) => `'${role}'`).join(' | ')};`,
            // What Prettier writes once the union outgrows printWidth: one member per line, each after a `|`, the first one too.
            'one member per line, after a leading |': `export type ChartRole =\n${roles.map((role) => `    | '${role}'`).join('\n')};`,
        };
        for (const [form, source] of Object.entries(forms)) {
            expect(scrapeChartRoles(source), `${form}: the union is not read as written — a role the scrape misses leaves the parity gate`).toEqual({roles, declarations: 1, unread: []});
        }

        // One leading `|` is the syntax's; anything else that is not a quoted role is a member the scrape must name.
        const unreadable = {
            'an empty member in the middle': "export type ChartRole = '--lf-surface-card' | | '--lf-info';",
            'a second leading |': "export type ChartRole =\n    | | '--lf-surface-card'\n    | '--lf-info';",
            'a type, not a quoted role': "export type ChartRole = '--lf-surface-card' | string;",
            'a double-quoted role': `export type ChartRole = '--lf-surface-card' | "--lf-info";`,
        };
        expect(Object.fromEntries(Object.entries(unreadable).map(([what, source]) => [what, scrapeChartRoles(source).unread])), 'a member the scrape cannot read went unnamed: the parity gate would skip it in silence').toEqual({
            'an empty member in the middle': [''],
            'a second leading |': [''],
            'a type, not a quoted role': ['string'],
            'a double-quoted role': ['"--lf-info"'],
        });
    });

    it('positive control: every role of the union is read by chart code, directly or through readableText, or waits for its reader — the gate checks no dead role', () => {
        const {direct, readableTextCallers} = chartCodeReads();
        expect(direct.size, 'barrier: the scan finds charts reading roles with .color()').toBeGreaterThan(0);
        expect(readableTextCallers.length, 'barrier: a chart picks a readable text with .readableText()').toBeGreaterThan(0);
        const throughReadableText = rolesReadByReadableText();
        expect([...throughReadableText], 'barrier: readableText reads the two texts').toEqual(expect.arrayContaining(['--lf-text-primary', '--lf-text-on-inverse']));

        const read = new Set([...direct, ...throughReadableText]);
        expect(
            ROLES.filter((role) => !read.has(role) && !PENDING.has(role)),
            'roles of ChartRole that no chart code reads and no batch is named to read (PENDING_READERS): remove them from the union and the stand-ins, or the chart meant to read them is missing',
        ).toEqual([]);
        expect(
            [...direct].filter((role) => !(ROLES as string[]).includes(role)),
            'chart code reads roles outside ChartRole',
        ).toEqual([]);
    });

    it('roles waiting for their reader: each is in ChartRole, and none is read yet — the batch that starts reading one removes its line', () => {
        expect(
            [...PENDING].filter((role) => !(ROLES as string[]).includes(role)),
            'PENDING_READERS names roles that are not in ChartRole: remove the stale lines',
        ).toEqual([]);

        const {direct} = chartCodeReads();
        expect(direct.size, 'barrier: the scan finds charts reading roles with .color(), so «not read yet» is about something').toBeGreaterThan(0);
        const read = new Set([...direct, ...rolesReadByReadableText()]);
        expect(
            [...PENDING].filter((role) => read.has(role)).map((role) => `remove ${role} from PENDING_READERS: production code reads it now`),
            'a role waiting for its reader is read: the hand-over is the reading batch removing its line',
        ).toEqual([]);
    });
});

/** A colour as the gate's resolver gives it: sRGB channels and alpha, 0–1 (`Rgba` in `theme-roles.mjs`). */
interface ResolvedColour {
    r: number;
    g: number;
    b: number;
    alpha: number;
}

/** How far a translucent stand-in's alpha may sit from the resolver's: a stand-in is written with a few decimals. */
const ALPHA_TOLERANCE = 1e-3;

/** An `rgba()` of four comma-separated numbers: what `toRgba` writes, and what zrender reads — it splits at commas, so it draws an `rgba()` without them black. */
const COMMA_RGBA = /^rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(?:\d*\.)?\d+\s*\)$/i;

/** Whether the resolver's colour is translucent: its stand-in is then an `rgba()`, compared channel by channel. */
function isTranslucent(resolved: ResolvedColour): boolean {
    return resolved.alpha < OPAQUE;
}

/** A translucent colour of the resolver as its stand-in should read, `rgba(r,g,b,a)` with the channels at 8 bits: for messages. */
function rgbaText(resolved: ResolvedColour): string {
    const [r, g, b] = [resolved.r, resolved.g, resolved.b].map((channel) => Math.round(channel * 255));
    return `rgba(${r},${g},${b},${Number(resolved.alpha.toFixed(4))})`;
}

/**
 * Why `standIn` is not the translucent colour tokens.css resolves to — `null` when it is: an `rgba(r,g,b,a)` in the
 * comma form, whose channels are the resolver's at 8 bits, as a canvas keeps them, and whose alpha is the resolver's
 * within ALPHA_TOLERANCE. Read with `parseRgba`, as the colours drawn from the roles read it.
 */
function translucentMismatch(standIn: string, resolved: ResolvedColour): string | null {
    if (!COMMA_RGBA.test(standIn.trim())) return `${standIn} is not an rgba(r,g,b,a)`;
    const parsed = parseRgba(standIn);
    if (parsed === null) return `${standIn} cannot be read`;
    const expected = [resolved.r, resolved.g, resolved.b].map((channel) => Math.round(channel * 255));
    const actual = [parsed.r, parsed.g, parsed.b];
    if (actual.some((channel, index) => channel !== expected[index])) return `${standIn}: channels ${actual.join(',')}, not ${expected.join(',')}`;
    if (Math.abs(parsed.alpha - resolved.alpha) > ALPHA_TOLERANCE) return `${standIn}: alpha ${parsed.alpha}, not ${resolved.alpha}`;
    return null;
}

describe('the parity gate — every stand-in is tokens.css, theme by theme', () => {
    const tokens = readTokens();

    it.each(ROLE_THEMES)('%s, %s theme', (role, theme) => {
        const resolved: ResolvedColour = resolveColour(tokens, `var(${role})`, theme);
        if (isTranslucent(resolved)) {
            const token = rgbaText(resolved);

            setRoleReader(() => '');
            const throughReader = chartRoles(theme === 'dark', null).color(role);
            expect(translucentMismatch(throughReader, resolved), `update the stand-in in roleColors.ts to tokens.css: ${role}, ${theme} theme, tokens.css resolves ${token}`).toBeNull();

            setRoleReader(null);
            const withoutReader = chartRoles(theme === 'dark').color(role);
            expect(translucentMismatch(withoutReader, resolved), `update the stand-in in roleColors.ts to tokens.css: ${role}, ${theme} theme, read with no reader and no page, tokens.css resolves ${token}`).toBeNull();
        } else {
            const token = toHex(resolved).toLowerCase();

            setRoleReader(() => '');
            const throughReader = chartRoles(theme === 'dark', null).color(role);
            expect(throughReader.toLowerCase(), `update the stand-in in roleColors.ts to tokens.css: ${role}, ${theme} theme, tokens.css resolves ${token}`).toBe(token);

            setRoleReader(null);
            const withoutReader = chartRoles(theme === 'dark').color(role);
            expect(withoutReader.toLowerCase(), `update the stand-in in roleColors.ts to tokens.css: ${role}, ${theme} theme, read with no reader and no page`).toBe(token);
        }
    });

    it('barrier: the translucent branch checks something — --lf-selected resolves translucent in both themes', () => {
        const translucent = ROLE_THEMES.filter(([role, theme]) => isTranslucent(resolveColour(tokens, `var(${role})`, theme))).map(([role, theme]) => `${role}, ${theme}`);
        expect(translucent, 'no translucent role where --lf-selected should be one: the rgba() comparison of the gate would pass on nothing').toEqual(expect.arrayContaining(['--lf-selected, light', '--lf-selected, dark']));
    });

    it('positive control: the translucent comparison takes the rgba() tokens.css resolves, and refuses a wrong channel, a wrong alpha and a #rrggbb', () => {
        // The light --lf-selected as the resolver gives it: #236b4d at 12 %.
        const selected: ResolvedColour = {r: 35 / 255, g: 107 / 255, b: 77 / 255, alpha: 0.12};
        expect(rgbaText(selected), 'the red message names the rgba() to write').toBe('rgba(35,107,77,0.12)');
        expect(translucentMismatch('rgba(35,107,77,0.12)', selected), 'the stand-in as roleColors.ts writes it').toBeNull();
        expect(translucentMismatch('rgba(35, 107, 77, 0.1205)', selected), 'spaces after the commas, and an alpha within the tolerance').toBeNull();

        const refused = {
            'a wrong channel': 'rgba(35,107,78,0.12)',
            'a wrong alpha': 'rgba(35,107,77,0.2)',
            'an alpha just outside the tolerance': 'rgba(35,107,77,0.122)',
            'a #rrggbb': '#236b4d',
            'a #rrggbbaa': '#236b4d1f',
            'an rgb() with no alpha': 'rgb(35,107,77)',
            'an rgba() without commas, which zrender draws black': 'rgba(35 107 77 / 0.12)',
        };
        expect(
            Object.entries(refused)
                .filter(([, standIn]) => translucentMismatch(standIn, selected) === null)
                .map(([what]) => what),
            'the comparison takes a stand-in that is not tokens.css: the gate would let it through',
        ).toEqual([]);
    });
});

describe('chartRoles without a page — the reader, the stand-ins, a #rrggbb', () => {
    it('premise: this is a node run, with no document', () => {
        expect(typeof document).toBe('undefined');
    });

    it('asks an injected reader before looking for any element, handing it the role and the scope', () => {
        const reader = vi.fn<RoleReader>(() => '#123456');
        setRoleReader(reader);

        expect(chartRoles(false, null).color('--lf-info')).toBe('#123456');
        expect(reader).toHaveBeenLastCalledWith('--lf-info', null);

        expect(chartRoles(true).color('--lf-danger'), 'no scope, no document: the reader is asked with null').toBe('#123456');
        expect(reader).toHaveBeenLastCalledWith('--lf-danger', null);

        // No DOM here: any object stands for the chart's element, which the reader receives untouched.
        const scope = {} as Element;
        expect(chartRoles(true, scope).color('--lf-surface-panel')).toBe('#123456');
        expect(reader).toHaveBeenLastCalledWith('--lf-surface-panel', scope);
    });

    it('hands back a #rrggbb exactly as the reader wrote it, whatever its case', () => {
        for (const value of ['#ABCDEF', '#abcdef', '#0a0B0c']) {
            setRoleReader(() => value);
            expect(chartRoles(false, null).color('--lf-surface-card')).toBe(value);
        }
    });

    it('lets dark pick the stand-in and nothing else: a value the reader gives is the same in both themes', () => {
        setRoleReader(() => '');
        expect(chartRoles(false, null).color('--lf-info'), 'barrier: the two stand-ins differ, so the flag has something to pick').not.toBe(chartRoles(true, null).color('--lf-info'));

        setRoleReader(() => '#0A0B0C');
        expect(chartRoles(false, null).color('--lf-info')).toBe('#0A0B0C');
        expect(chartRoles(true, null).color('--lf-info')).toBe('#0A0B0C');
    });

    it('stands in for any other notation: it needs a canvas, and a node run has none', () => {
        setRoleReader(() => '');
        const standIn = chartRoles(true, null).color('--lf-danger');
        for (const value of ['oklch(0.62 0.14 155)', 'color-mix(in oklab, #b42332 40%, #eee9de)', 'rgba(0, 0, 0, 0.5)', 'not a colour', '#12345', 'var(--lf-danger)']) {
            setRoleReader(() => value);
            expect(chartRoles(true, null).color('--lf-danger'), value).toBe(standIn);
        }
    });

    it('reads anew at every draw: a new chartRoles sees what the reader answers now', () => {
        let answer = '#111111';
        setRoleReader(() => answer);
        expect(chartRoles(false, null).color('--lf-surface-panel')).toBe('#111111');
        answer = '#222222';
        expect(chartRoles(false, null).color('--lf-surface-panel')).toBe('#222222');
    });
});

describe('readableText — the primary text or the inverse one, whichever reads better', () => {
    it.each(THEMES)('%s theme, on the stand-ins: the darker text on white, the lighter one on black', (theme) => {
        setRoleReader(() => '');
        const roles = chartRoles(theme === 'dark', null);
        const [primary, inverse] = [roles.color('--lf-text-primary'), roles.color('--lf-text-on-inverse')];
        expect(primary, 'barrier: two different texts to choose from').not.toBe(inverse);
        // The primary text is the dark one in the light theme, the light one in the dark theme.
        const [darker, lighter] = theme === 'light' ? [primary, inverse] : [inverse, primary];

        expect(roles.readableText('#ffffff')).toBe(darker);
        expect(roles.readableText('#000000')).toBe(lighter);
    });

    it('measures a translucent background over the card it reads: the same veil wants dark text on a white card, light text on a black one', () => {
        const page =
            (card: string): RoleReader =>
            (role) => {
                const set: Partial<Record<ChartRole, string>> = {'--lf-text-primary': '#000000', '--lf-text-on-inverse': '#ffffff', '--lf-surface-card': card};
                return set[role] ?? '';
            };
        const veil = 'rgba(0, 0, 0, 0.5)';

        setRoleReader(page('#ffffff'));
        expect(chartRoles(false, null).readableText(veil)).toBe('#000000');
        setRoleReader(page('#000000'));
        expect(chartRoles(false, null).readableText(veil)).toBe('#ffffff');
    });

    it('reads its roles at call time, through the reader: the texts the page sets, not constants', () => {
        const set: Partial<Record<ChartRole, string>> = {'--lf-text-primary': '#000001', '--lf-text-on-inverse': '#FFFFFE'};
        setRoleReader((role) => set[role] ?? '');
        const roles = chartRoles(false, null);
        expect(roles.readableText('#F0F0F0')).toBe('#000001');
        expect(roles.readableText('#101010')).toBe('#FFFFFE');
    });
});
