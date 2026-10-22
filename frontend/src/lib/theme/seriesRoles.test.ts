/**
 * seriesRoles — the roles the chart series stand on (DV-10, C2): the parity gate, the helpers, the use.
 *
 * - **Parity.** `SERIES_ROLE_VALUES` holds each role as tokens.css resolves it, per theme; `lib/theme/` is outside the
 *   colour ratchet, so nothing but this gate keeps the rows equal to tokens.css, by the resolver the other gates use
 *   (`scripts/theme/theme-roles.mjs`). Its red says what to do: «update the row in seriesRoles.ts to tokens.css».
 * - **Use.** Every role of the table is used by `chartTheme.ts` (no dead row), and every `rolePair('--lf-…')` names a row.
 * - **Helpers.** `rolePair`, `rolePairSplit`, `rolePairAlpha`; the getters of `pairNow`/`roleNow` follow the theme class
 *   of `<html>`.
 *
 * jsdom env, for the theme class.
 *
 * @vitest-environment jsdom
 * @module lib/theme/seriesRoles.test
 */
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {afterEach, describe, expect, it} from 'vitest';

import {listSources, readTokens, resolveColour, SRC_DIR, toHex} from '../../../scripts/theme/theme-roles.mjs';

import {parseRgba} from './colorAlpha';
import {pairNow, rolePair, rolePairAlpha, rolePairSplit, roleNow, roleNowAlpha, SERIES_ROLE_VALUES, type SeriesRole} from './seriesRoles';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const THEMES = ['light', 'dark'] as const;
const ROLES = Object.keys(SERIES_ROLE_VALUES) as SeriesRole[];

afterEach(() => {
    document.documentElement.classList.remove('dark');
});

describe('the parity gate — every row is tokens.css, theme by theme', () => {
    const tokens = readTokens();

    it.each(ROLES.flatMap((role) => THEMES.map((theme) => [role, theme] as const)))('%s, %s theme', (role, theme) => {
        const resolved = resolveColour(tokens, `var(${role})`, theme);
        const row = SERIES_ROLE_VALUES[role][theme];
        if (resolved.alpha < 1 - 1e-9) {
            const parsed = parseRgba(row);
            const expected = [resolved.r, resolved.g, resolved.b].map((channel: number) => Math.round(channel * 255));
            expect(parsed, `update the row in seriesRoles.ts to tokens.css: ${role}, ${theme} theme: ${row} is not an rgba()`).not.toBeNull();
            expect([parsed!.r, parsed!.g, parsed!.b], `update the row in seriesRoles.ts to tokens.css: ${role}, ${theme} theme, the channels`).toEqual(expected);
            expect(Math.abs(parsed!.alpha - resolved.alpha), `update the row in seriesRoles.ts to tokens.css: ${role}, ${theme} theme, the alpha`).toBeLessThan(1e-3);
        } else {
            expect(row.toLowerCase(), `update the row in seriesRoles.ts to tokens.css: ${role}, ${theme} theme, tokens.css resolves ${toHex(resolved).toLowerCase()}`).toBe(toHex(resolved).toLowerCase());
        }
    });

    it('barrier: the table holds the roles the series stand on, and a translucent one for the parity gate to read', () => {
        expect(ROLES.length).toBeGreaterThan(15);
        expect(ROLES).toEqual(expect.arrayContaining(['--lf-gain', '--lf-loss', '--lf-info', '--lf-warning', '--lf-surface-overlay']));
        expect(resolveColour(tokens, 'var(--lf-surface-overlay)', 'light').alpha, 'the overlay is translucent: the rgba() branch checks something').toBeLessThan(1);
    });
});

describe('the use — no dead row, no unknown role', () => {
    const source = readFileSync(path.join(HERE, 'chartTheme.ts'), 'utf-8') + readFileSync(path.join(HERE, 'chartColorScales.ts'), 'utf-8');
    // The roles the series tables name: the arguments of the helpers, and a row read by name. The neutrals read other roles through chartRoles.
    const named = new Set(
        source
            .split('\n')
            .filter((line) => /\b(?:rolePair|rolePairSplit|rolePairAlpha|roleNow|roleNowAlpha)\(|SERIES_ROLE_VALUES\[/.test(line))
            .flatMap((line) => [...line.matchAll(/'(--lf-[a-z0-9-]+)'/g)].map((match) => match[1])),
    );

    it('every role the chart tables name is a row of the table', () => {
        expect(
            [...named].filter((role) => !(ROLES as string[]).includes(role)),
            'chartTheme.ts names a role seriesRoles.ts does not hold: add its row (and its parity)',
        ).toEqual([]);
    });

    it('every row is named by the chart tables, or read by the treemap scale', () => {
        expect(
            ROLES.filter((role) => !named.has(role)),
            'a row of seriesRoles.ts no table uses: remove it',
        ).toEqual([]);
    });
});

describe('the helpers', () => {
    it('rolePair gives both themes of a role, as a copy', () => {
        expect(rolePair('--lf-gain')).toEqual({light: '#18794e', dark: '#5ed69a'});
        expect(rolePair('--lf-gain')).not.toBe(SERIES_ROLE_VALUES['--lf-gain']);
    });

    it('rolePairSplit takes the light of one role and the dark of another', () => {
        expect(rolePairSplit('--lf-cat-hold-on-soft', '--lf-border-input')).toEqual({light: '#5c677a', dark: '#606f6a'});
    });

    it('rolePairAlpha writes the role at an opacity per theme, rgba() with commas', () => {
        expect(rolePairAlpha('--lf-info', 0.08, 0.1)).toEqual({light: 'rgba(21,94,239,0.08)', dark: 'rgba(63,134,250,0.1)'});
        expect(rolePairAlpha('--lf-info', 0.5)).toEqual({light: 'rgba(21,94,239,0.5)', dark: 'rgba(63,134,250,0.5)'});
    });

    it('roleNow and pairNow follow the dark class of <html>, and read the light theme with none', () => {
        expect(roleNow('--lf-loss')).toBe('#c82838');
        expect(roleNowAlpha('--lf-loss', 0.5)).toBe('rgba(200,40,56,0.5)');
        document.documentElement.classList.add('dark');
        expect(roleNow('--lf-loss')).toBe('#ff7a86');
        expect(roleNowAlpha('--lf-loss', 0.5)).toBe('rgba(255,122,134,0.5)');
        expect(pairNow({light: 'L', dark: 'D'})).toBe('D');
    });
});

/**
 * The leaves of `chartTheme.ts` that are getters (a string the same in both themes), and the objects that hold them. A
 * caller that copies a leaf once keeps the theme it read; one that reads it where it draws, or in a `$derived`, an
 * `$effect` or a template, follows the theme (`seriesRoles.reactive.svelte.test.ts`).
 */
const GETTER_LEAVES =
    /\b(?:PRICE_SERIES\.(?:pendingEditPoint|comparisonMarkerFallback)|CHART_GAIN_LOSS\.tooltipDelta\.(?:gain|loss)|candlestickBox\.seriesFallback|SIGNAL_COLORS\.(?:roles\.\w+|legendBarPreview\.(?:up|down)|measure)|PERFORMANCE_COLORS\.badgeText|TREEMAP_COLORS\.(?:noPnl|tileLabel|tileLabelShadow)|RISK_OVERLAY_COLORS\.\w+|pulseBand\.glow|ALLOCATION_CHART_COLORS\.iconBubble)\b/;

/**
 * Callers that copy a getter once, each with what it costs and who can cure it. The list only shrinks: a caller that
 * stops copying must leave it.
 */
// The LineChart pending-edit copy was cured by Y (`ebe64831e`): no known copy is left.
const KNOWN_COPIES: Readonly<Record<string, string>> = {};

describe('the callers — no production source copies a theme-dependent getter once, but the known ones', () => {
    /** Why a line copies a getter once, or `null`: a module-level constant, a destructuring or prop default, or a spread. */
    function copyOf(line: string): string | null {
        if (/\.\.\.[\w.]*(?:SIGNAL_COLORS\.roles|tooltipDelta|legendBarPreview)\b/.test(line)) return 'a spread of the getter object';
        if (!GETTER_LEAVES.test(line)) return null;
        if (/^(?:export\s+)?(?:const|let|var)\s/.test(line)) return 'a module-level constant';
        if (/^\s+\w+\s*=\s*[\w.]+,?\s*$/.test(line)) return 'a default value (a prop fallback or a destructuring default)';
        return null;
    }

    const copies = new Map<string, string[]>();
    for (const rel of listSources()) {
        if (rel.startsWith('lib/theme/') || /\.test\.ts$/.test(rel)) continue;
        const lines = readFileSync(path.join(SRC_DIR, rel), 'utf-8').split('\n');
        const found = lines.flatMap((line, index) => {
            const why = copyOf(line);
            return why ? [`${rel}:${index + 1} (${why})`] : [];
        });
        if (found.length > 0) copies.set(rel, found);
    }

    it('barrier: the scan recognises each form of a copy', () => {
        expect(copyOf('const COLOR = RISK_OVERLAY_COLORS.simulation;')).toMatch(/module-level/);
        expect(copyOf('        pendingColor = PRICE_SERIES.pendingEditPoint,')).toMatch(/default value/);
        expect(copyOf('    ...SIGNAL_COLORS.legendBarPreview,')).toMatch(/spread/);
        expect(copyOf('    color: RISK_OVERLAY_COLORS.simulation,')).toBeNull();
        expect(copyOf('const ROLE_COLORS = SIGNAL_COLORS.roles;')).toBeNull();
    });

    it('every copy is a known one, and every known one is still there', () => {
        expect(
            [...copies.entries()].filter(([rel]) => !(rel in KNOWN_COPIES)).flatMap(([, found]) => found),
            'a source copies a getter of chartTheme.ts once, so after a theme switch with no reload it keeps the old theme: read it where it draws (or in a $derived)',
        ).toEqual([]);
        expect(
            Object.keys(KNOWN_COPIES).filter((rel) => !copies.has(rel)),
            'a known copy is gone: remove it from KNOWN_COPIES',
        ).toEqual([]);
    });
});
