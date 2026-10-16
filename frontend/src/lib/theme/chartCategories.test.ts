/**
 * chartCategories — the fixed colour of every category the charts draw (DV: the designer's round 2, GR1–GR5, approved
 * by the developer as D-T17), and the contract with the Designer Lab (C1–C3).
 *
 * What is pinned, one concern per block:
 *
 * 1. **The designer's values.** Every key of both tables and the two buckets, both themes, read through
 *    `categoryColor`, against her tables as transcribed below from `risposta-2-grafici-originale.txt` (tables 3.2 A and
 *    3.2 B of `LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/designer-feedback/2026-10-15-round2-palette/`;
 *    the original wins over the README). The lookup ignores case, spaces and underscores — `lookupKey`, exported so the
 *    Designer Lab keys its edits the same way; a key outside the tables — an unresolved subtype included — reads as
 *    unclassified.
 * 2. **C1, one read point.** The module exports exactly what its header documents, and no colour at any depth: the
 *    tables cannot be read past the hook.
 * 3. **C2, one literal per line.** Every colour of the file sits alone on a `light:`/`dark:` line, and those lines are
 *    the colours `categoryColor` returns: the Lab exports an edit by file and line.
 * 4. **The sequences (GR5).** A sequence in order, then one shade further at each round, 98 distinct colours for the 14
 *    sectors; the Growth chart's broker lines are the first eight types the same way, 56 distinct colours (DV-8), the
 *    shades toward the poles the chart passes or else the page's card, read only from the ninth line on; read at each
 *    draw so a Designer Lab edit reaches them (`growthBrokerColor`, TD-1b).
 * 5. **C3, the hook.** In a debug build the Lab answers first; a null answer, a missing hook or the flag off leave the
 *    table's value. In a release build the hook is gone: the esbuild the release build minifies with, run on this
 *    source with the define a release build sets, leaves no trace of it.
 * 6. **Key coverage against the backend.** Every `FinancialSector` value has a sector colour and every sector key is
 *    one; every `AssetType` value, resolved to its family, has a type colour and every type key is a family; the
 *    buckets are the backend's. Scraped as text, each scrape guarded against reading nothing.
 * 7. **GR2.** No category takes the semantic loss red or gain green; the brand's sage is the cash's alone.
 * 8. **Distinguishability.** Within each table and theme every pair is at least ΔE00 10 apart, except the pairs the
 *    round-2 analysis measured closer (`analisi.md` §4), each listed with its measure. The values are the designer's
 *    and are not corrected here: the list is what her round 3 starts from. **The two buckets join both tables** for
 *    this check: the engine draws the cash and the unclassified beside the types and beside the sectors alike, so a
 *    slice of either can touch any category, and §4 already measures one such pair (Financials · Liquidity). With both
 *    buckets in, the pairs under 10 are exactly the analysis's ten.
 *
 * The ruler (CIEDE2000, `$test/colorDistance`) is proven on published data before the gate reads a single distance.
 *
 * Node env: pure functions, sources read as text with `fs`, esbuild run in process.
 *
 * @module lib/theme/chartCategories.test
 */
import {existsSync, readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {afterEach, describe, expect, it, vi} from 'vitest';

import {ciede2000, deltaE00, labOf, SHARMA_PAIRS, SRGB_LAB} from '$test/colorDistance';

import {CATEGORY_BUCKETS, CATEGORY_KEYS, CATEGORY_SEQUENCE, categoryColor, type CategoryKind, isUnclassifiedCountry, KEYLESS_SEQUENCE, lookupKey, sequenceColor} from './chartCategories';
import {growthBrokerColor} from './chartPalettes';
import {familyShade, shadePoles} from './chartShades';
import {setRoleReader} from './roleColors';

// =============================================================================
// The designer's tables (round 2), as she wrote them: key, light, dark
// =============================================================================

type Row = readonly [key: string, light: string, dark: string];

/** Table 3.2 A, «Tipi di asset»: the asset-type families, in her order. */
const DESIGNER_TYPES: readonly Row[] = [
    ['STOCK', '#6D28D9', '#A78BFA'],
    ['ETF', '#1D5BD8', '#60A5FA'],
    ['BOND', '#0E7490', '#22D3EE'],
    ['CRYPTO', '#D97706', '#FBBF24'],
    ['FUND', '#4338CA', '#818CF8'],
    ['HOLD', '#5F6B7A', '#94A3B8'],
    ['CROWDFUND', '#0D9488', '#2DD4BF'],
    ['COMMODITY', '#C25E00', '#FB923C'],
    ['REAL_ESTATE', '#B45309', '#F59E0B'],
    ['INDEX', '#A21CAF', '#E879F9'],
    ['OTHER', '#6E7A74', '#7F8C87'],
];

/** Table 3.2 B, «Settori»: the sectors, in her order. */
const DESIGNER_SECTORS: readonly Row[] = [
    ['Industrials', '#475569', '#94A3B8'],
    ['Technology', '#1D5BD8', '#60A5FA'],
    ['Financials', '#0F766E', '#2DD4BF'],
    ['Consumer Discretionary', '#7C3AED', '#A78BFA'],
    ['Health Care', '#0284C7', '#38BDF8'],
    ['Real Estate', '#B45309', '#FBBF24'],
    ['Basic Materials', '#9A3412', '#FB923C'],
    ['Energy', '#D97706', '#FACC15'],
    ['Consumer Staples', '#4D7C0F', '#A3E635'],
    ['Telecommunication', '#4338CA', '#818CF8'],
    ['Utilities', '#0E7490', '#22D3EE'],
    ['Corporate Bonds', '#86198F', '#E879F9'],
    ['Government Bonds', '#1E3A8A', '#93C5FD'],
    ['Other', '#6E7A74', '#7F8C87'],
];

/** The engine's two buckets, beside both tables: the cash (GR3, the brand's sage) and the unclassified (a fog grey). */
const DESIGNER_BUCKETS: readonly Row[] = [
    ['Liquidity', '#2D6A54', '#429E79'],
    ['Unknown', '#94A09B', '#52605B'],
];

const UNCLASSIFIED = {light: '#94A09B', dark: '#52605B'} as const;
const KINDS: readonly CategoryKind[] = ['type', 'sector'];
const THEMES = [false, true] as const;
const themeName = (dark: boolean): 'light' | 'dark' => (dark ? 'dark' : 'light');
/** The two themes as `it.each` rows: a name for the title, the flag for the call. */
const THEME_CASES = THEMES.map((dark) => [themeName(dark), dark] as const);
const DESIGNER: Readonly<Record<CategoryKind, readonly Row[]>> = {type: DESIGNER_TYPES, sector: DESIGNER_SECTORS};

/** Two colours alike, whatever the letter case of their hex. */
const same = (colour: string) => colour.toUpperCase();

/** The dark theme's card in the designer's round 2 (`--lf-surface-card`): the near pole of the dark shades. */
const DARK_CARD = '#151B19';

afterEach(() => {
    vi.unstubAllGlobals();
});

// =============================================================================
// 1. The designer's values, through the one read point
// =============================================================================

describe("categoryColor — the designer's values (round 2), both themes", () => {
    it('lists her keys in her order: eleven families, fourteen sectors, the two buckets apart', () => {
        expect(CATEGORY_KEYS.type).toEqual(DESIGNER_TYPES.map(([key]) => key));
        expect(CATEGORY_KEYS.sector).toEqual(DESIGNER_SECTORS.map(([key]) => key));
        expect(CATEGORY_BUCKETS).toEqual(DESIGNER_BUCKETS.map(([key]) => key));
    });

    const ROWS = KINDS.flatMap((kind) => [...DESIGNER[kind], ...DESIGNER_BUCKETS].map(([key, light, dark]) => [kind, key, light, dark] as const));

    it.each(ROWS)('%s %s: %s light, %s dark', (kind, key, light, dark) => {
        const [readLight, readDark] = THEMES.map((theme) => categoryColor(kind, key, theme));
        expect(readLight, 'light: a #rrggbb').toMatch(/^#[0-9a-f]{6}$/i);
        expect(readDark, 'dark: a #rrggbb').toMatch(/^#[0-9a-f]{6}$/i);
        expect(same(readLight), 'light').toBe(same(light));
        expect(same(readDark), 'dark').toBe(same(dark));
    });
});

describe('categoryColor — the lookup', () => {
    it('ignores case, spaces and underscores: the forms a key arrives in all find it', () => {
        const forms: ReadonlyArray<readonly [CategoryKind, string, readonly string[]]> = [
            ['sector', 'Health Care', ['health_care', 'HEALTH CARE', 'healthcare', 'HealthCare', ' Health  Care ']],
            ['sector', 'Consumer Discretionary', ['consumer_discretionary', 'CONSUMER DISCRETIONARY']],
            ['type', 'REAL_ESTATE', ['real estate', 'Real_Estate', 'realestate']],
            ['type', 'ETF', ['etf', 'Etf']],
            ['type', 'Liquidity', ['LIQUIDITY', 'liquidity']],
            ['sector', 'Unknown', ['UNKNOWN', 'unknown']],
        ];
        for (const [kind, key, variants] of forms) {
            for (const dark of THEMES) {
                const expected = categoryColor(kind, key, dark);
                if (key !== 'Unknown') expect(same(expected), `barrier: ${key} itself reads a colour of its own, not the unclassified one`).not.toBe(same(UNCLASSIFIED[themeName(dark)]));
                for (const variant of variants) expect(categoryColor(kind, variant, dark), `${kind} ${JSON.stringify(variant)}, ${themeName(dark)}`).toBe(expected);
            }
        }
    });

    it('reads any key outside the tables as unclassified: unknown words, the empty key, the names of Object.prototype', () => {
        for (const kind of KINDS) {
            for (const key of ['NOT_A_CATEGORY', '', 'constructor', '__proto__', 'toString']) {
                for (const dark of THEMES) expect(same(categoryColor(kind, key, dark)), `${kind} ${JSON.stringify(key)}, ${themeName(dark)}`).toBe(same(UNCLASSIFIED[themeName(dark)]));
            }
        }
    });

    it("keeps the two tables apart: a type is no sector and a sector no type, even where the designer's colours meet", () => {
        for (const dark of THEMES) {
            const fog = same(UNCLASSIFIED[themeName(dark)]);
            expect(same(categoryColor('sector', 'ETF', dark)), 'ETF as a sector').toBe(fog);
            expect(same(categoryColor('type', 'Technology', dark)), 'Technology as a type').toBe(fog);
            expect(same(categoryColor('type', 'Health Care', dark)), 'Health Care as a type').toBe(fog);
        }
    });

    it('leaves a subtype to its caller: ETF_STOCK unresolved reads unclassified, its family ETF does not', () => {
        for (const dark of THEMES) {
            const fog = same(UNCLASSIFIED[themeName(dark)]);
            expect(same(categoryColor('type', 'ETF', dark)), 'barrier: the family has a colour').not.toBe(fog);
            expect(same(categoryColor('type', 'ETF_STOCK', dark)), 'a subtype is resolved by the caller (assetTypeFamily), not here').toBe(fog);
        }
    });

    it('isUnclassifiedCountry: the engine’s Unknown and a provider’s Other, in any case — nothing else', () => {
        for (const key of ['Unknown', 'unknown', 'UNKNOWN', 'Other', 'OTHER', ' other ']) expect(isUnclassifiedCountry(key), JSON.stringify(key)).toBe(true);
        for (const key of ['ITA', 'Others', 'Liquidity', 'european_union', '']) expect(isUnclassifiedCountry(key), JSON.stringify(key)).toBe(false);
    });

    it('lookupKey, the key the lookup compares (exported for the Designer Lab): one key for every form a key arrives in, unchanged when applied again', () => {
        const key = lookupKey('Health Care');
        expect(key, 'barrier: another category keeps another key, so one key for all forms is no constant').not.toBe(lookupKey('Technology'));

        for (const form of ['HEALTH_CARE', 'healthcare', ' health care ']) expect(lookupKey(form), JSON.stringify(form)).toBe(key);
        for (const form of ['Health Care', 'HEALTH_CARE', 'healthcare', ' health care ', ...CATEGORY_KEYS.type, ...CATEGORY_KEYS.sector, ...CATEGORY_BUCKETS]) expect(lookupKey(lookupKey(form)), `idempotent: ${JSON.stringify(form)}`).toBe(lookupKey(form));
    });
});

// =============================================================================
// 2. C1 — one read point: the module exports no colour
// =============================================================================

/** Every export, read whole. Through `vi.importActual`, as `chartTheme.test.ts` reads its tables, so knip does not take the walk for a use of each export. */
const NAMESPACE: Record<string, unknown> = await vi.importActual('./chartCategories');

/** What the module's header documents, the type aside (types are erased). */
const DOCUMENTED_EXPORTS = ['CATEGORY_BUCKETS', 'CATEGORY_KEYS', 'CATEGORY_SEQUENCE', 'KEYLESS_SEQUENCE', 'categoryColor', 'isUnclassifiedCountry', 'lookupKey', 'sequenceColor'];

/** Every path under `value`, at any depth, that holds a colour or a `{light, dark}` pair. */
function colourLeaks(value: unknown, at: string): string[] {
    if (typeof value === 'string') return /^#[0-9a-f]{3,8}$/i.test(value) || /^(?:rgba?|hsla?|oklch|oklab|color-mix)\(/i.test(value) ? [at] : [];
    if (value === null || typeof value !== 'object') return [];
    const pair = 'light' in value || 'dark' in value ? [`${at} (a light/dark pair)`] : [];
    return [...pair, ...Object.entries(value).flatMap(([key, child]) => colourLeaks(child, `${at}.${key}`))];
}

describe('C1 — one read point: nothing but categoryColor hands out a category colour', () => {
    it('exports exactly what its header documents', () => {
        expect(Object.keys(NAMESPACE).sort()).toEqual([...DOCUMENTED_EXPORTS].sort());
    });

    it('exports no colour and no light/dark pair, at any depth: its lists hold keys', () => {
        expect(Object.entries(NAMESPACE).flatMap(([name, value]) => colourLeaks(value, name))).toEqual([]);
    });

    it('positive control: the walk names a table, and its colours, where one is exported', () => {
        const leaky = {TABLE: {ETF: {light: '#1D5BD8', dark: '#60A5FA'}}, LIST: ['STOCK', 'rgb(1, 2, 3)']};
        expect(colourLeaks(leaky, 'leaky')).toEqual(['leaky.TABLE.ETF (a light/dark pair)', 'leaky.TABLE.ETF.light', 'leaky.TABLE.ETF.dark', 'leaky.LIST.1']);
    });
});

// =============================================================================
// 3. C2 — one literal per line
// =============================================================================

const HERE = path.dirname(fileURLToPath(import.meta.url));
/** `theme` → `lib` → `src` → `frontend` */
const FRONTEND_DIR = path.resolve(HERE, '..', '..', '..');
const REPO_DIR = path.resolve(FRONTEND_DIR, '..');

const CHART_CATEGORIES_TS = path.join(HERE, 'chartCategories.ts');
const SECTOR_PY = path.join(REPO_DIR, 'backend', 'app', 'utils', 'asset', 'sector.py');
const MODELS_PY = path.join(REPO_DIR, 'backend', 'app', 'db', 'models.py');
const ASSET_TYPES_TS = path.join(FRONTEND_DIR, 'src', 'lib', 'utils', 'assetTypes.ts');

function read(file: string): string {
    expect(existsSync(file), `${file} does not exist: this test reads it as text, so a move or a rename must stop it rather than silently read nothing`).toBe(true);
    return readFileSync(file, 'utf-8');
}

describe('C2 — one literal per line: the Lab edits a colour by its file and line', () => {
    it('sets every colour of the file alone on a `light:` or `dark:` line, one line per value categoryColor returns', () => {
        const source = read(CHART_CATEGORIES_TS);
        const literalLines = source
            .split('\n')
            .map((line) => /^\s*(light|dark): '(#[0-9A-Fa-f]{6})',$/.exec(line))
            .filter((match) => match !== null);
        const everyHex = source.match(/#[0-9A-Fa-f]{6}\b/g) ?? [];

        expect(literalLines.length, 'barrier: the scan finds the literal lines').toBeGreaterThan(0);
        expect(everyHex.length, 'a colour of the file sits elsewhere than alone on its own light:/dark: line — inline in a pair, in an expression, in a comment').toBe(literalLines.length);

        // The buckets are declared once and shared by both tables.
        for (const dark of THEMES) {
            const theme = themeName(dark);
            const onLines = literalLines.filter((match) => match[1] === theme).map((match) => same(match[2]));
            const returned = [...KINDS.flatMap((kind) => CATEGORY_KEYS[kind].map((key) => categoryColor(kind, key, dark))), ...CATEGORY_BUCKETS.map((bucket) => categoryColor('type', bucket, dark))].map(same);
            expect(onLines.length, `${theme}: one line per key of both tables and per bucket`).toBe(CATEGORY_KEYS.type.length + CATEGORY_KEYS.sector.length + CATEGORY_BUCKETS.length);
            expect([...onLines].sort(), `${theme}: the lines hold exactly the colours categoryColor returns`).toEqual([...returned].sort());
        }
    });
});

// =============================================================================
// 4. The sequences (GR5) and the Growth chart's broker lines
// =============================================================================

describe('sequenceColor — a sequence in order, then one shade further at each round (GR5)', () => {
    it('CATEGORY_SEQUENCE is the first eight types of her table; KEYLESS_SEQUENCE her fourteen sectors, in order', () => {
        expect(CATEGORY_SEQUENCE).toEqual(['STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND', 'HOLD', 'CROWDFUND', 'COMMODITY']);
        expect(CATEGORY_SEQUENCE).toEqual(CATEGORY_KEYS.type.slice(0, CATEGORY_SEQUENCE.length));
        expect(KEYLESS_SEQUENCE).toEqual(DESIGNER_SECTORS.map(([key]) => key));
    });

    it.each(THEME_CASES)('%s: the first round is the sequence itself, in order, the base colours unshaded', (_theme, dark) => {
        const poles = shadePoles(dark, DARK_CARD);
        const sectors = KEYLESS_SEQUENCE.map((_, rank) => same(sequenceColor('sector', KEYLESS_SEQUENCE, rank, dark, poles)));
        expect(sectors).toEqual(DESIGNER_SECTORS.map((row) => same(dark ? row[2] : row[1])));
        const owners = CATEGORY_SEQUENCE.map((_, rank) => same(sequenceColor('type', CATEGORY_SEQUENCE, rank, dark, poles)));
        expect(owners).toEqual(DESIGNER_TYPES.slice(0, CATEGORY_SEQUENCE.length).map((row) => same(dark ? row[2] : row[1])));
    });

    it.each(THEME_CASES)('%s: rank 14 of the sectors is the first sector one shade on, 15 the second, 28 the first two shades on', (_theme, dark) => {
        const poles = shadePoles(dark, DARK_CARD);
        const base = (key: string) => categoryColor('sector', key, dark);
        expect(sequenceColor('sector', KEYLESS_SEQUENCE, 14, dark, poles)).toBe(familyShade(base(KEYLESS_SEQUENCE[0]), 1, poles));
        expect(sequenceColor('sector', KEYLESS_SEQUENCE, 15, dark, poles)).toBe(familyShade(base(KEYLESS_SEQUENCE[1]), 1, poles));
        expect(sequenceColor('sector', KEYLESS_SEQUENCE, 27, dark, poles)).toBe(familyShade(base(KEYLESS_SEQUENCE[13]), 1, poles));
        expect(sequenceColor('sector', KEYLESS_SEQUENCE, 28, dark, poles)).toBe(familyShade(base(KEYLESS_SEQUENCE[0]), 2, poles));
        expect(same(sequenceColor('sector', KEYLESS_SEQUENCE, 14, dark, poles)), 'barrier: a shade is not its base').not.toBe(same(base(KEYLESS_SEQUENCE[0])));
    });

    it.each(THEME_CASES)('%s: the fourteen sectors give 98 distinct colours before they cycle, never a silent repeat', (_theme, dark) => {
        const poles = shadePoles(dark, DARK_CARD);
        const colours = Array.from({length: 99}, (_, rank) => same(sequenceColor('sector', KEYLESS_SEQUENCE, rank, dark, poles)));
        expect(new Set(colours.slice(0, 98)).size).toBe(98);
        expect(colours[98], 'rank 98 starts the cycle again at the first shade').toBe(colours[14]);
    });
});

describe('growthBrokerColor — the Growth chart’s broker lines (GR5, TD-1b, DV-8)', () => {
    /** The designer's colours of her first eight types, in her order, as `same` reads them: the bases of lines 0–7. */
    function designerEight(dark: boolean): string[] {
        return CATEGORY_SEQUENCE.map((key) => {
            const row = DESIGNER_TYPES.find(([type]) => type === key);
            if (!row) throw new Error(`${key} is not a type of the designer's table`);
            return same(dark ? row[2] : row[1]);
        });
    }

    /** The roles read while `draw` runs, through an injected reader that answers none: the stand-ins stand. */
    function rolesReadBy(draw: () => unknown): string[] {
        const read: string[] = [];
        setRoleReader((role) => {
            read.push(role);
            return '';
        });
        draw();
        setRoleReader(null);
        return read;
    }

    afterEach(() => {
        setRoleReader(null);
    });

    it.each(THEME_CASES)("%s: lines 0–7 take the designer's first eight types, in her order", (_theme, dark) => {
        const eight = designerEight(dark);
        expect(eight, 'barrier: eight distinct colours, so a line out of place is seen').toHaveLength(8);
        expect(new Set(eight).size).toBe(8);

        expect(eight.map((_, index) => same(growthBrokerColor(index, dark)))).toEqual(eight);
    });

    it.each(THEME_CASES)('%s: from line 8 the same eight, one shade further at each round, toward the poles of the page’s card (DV-8)', (_theme, dark) => {
        // With no tokens.css the page's card is the stand-in of `--lf-surface-card`, DARK_CARD in the dark theme; the
        // light theme's poles are literals, whatever the card.
        const poles = shadePoles(dark, DARK_CARD);
        const eight = designerEight(dark);
        const firstShades = eight.map((base) => same(familyShade(base, 1, poles)));
        expect(
            firstShades.filter((shade, rank) => shade === eight[rank]),
            'barrier: a shade is not its base, so a repeat of the eight is seen',
        ).toEqual([]);

        expect(
            eight.map((_, rank) => same(growthBrokerColor(eight.length + rank, dark))),
            'lines 8–15: the eight, one shade on',
        ).toEqual(firstShades);

        // Eight rounds: the bases, their six shades, and the round the cycle restarts with.
        const lines = Array.from({length: 64}, (_, index) => growthBrokerColor(index, dark));
        expect(lines, 'every line: the sequence of the eight types, on the default poles').toEqual(lines.map((_, index) => sequenceColor('type', CATEGORY_SEQUENCE, index, dark, poles)));
    });

    it.each(THEME_CASES)('%s: lines 0–55 are 56 distinct colours, never a silent repeat; line 56 starts the cycle again at the first shade', (_theme, dark) => {
        // The eight types, each its base and its six GR4 shades.
        const lines = Array.from({length: 57}, (_, index) => same(growthBrokerColor(index, dark)));
        expect(new Set(lines.slice(0, 56)).size).toBe(56);
        expect(lines[56], 'line 56 starts the cycle again at the first shade, by design').toBe(lines[8]);
    });

    it('dark: shades toward the poles it is given, else toward the page’s card as read at the call', () => {
        const black = shadePoles(true, '#000000');
        const stock = designerEight(true)[0];
        const onBlack = familyShade(stock, 1, black);
        expect(same(onBlack), 'barrier: a black card shades line 8 otherwise than the default card, so the poles used show').not.toBe(same(familyShade(stock, 1, shadePoles(true, DARK_CARD))));

        expect(growthBrokerColor(8, true, black), 'explicit poles win over the default ones').toBe(onBlack);

        setRoleReader((role) => (role === '--lf-surface-card' ? '#000000' : ''));
        expect(growthBrokerColor(8, true), 'no poles given: those of the card the page has at the call, not of a fixed one').toBe(onBlack);
    });

    it.each(THEME_CASES)('%s: reads the page’s card only where a shade needs the default poles — not for lines 0–7, not when the poles are given', (_theme, dark) => {
        expect(
            rolesReadBy(() => CATEGORY_SEQUENCE.map((_, index) => growthBrokerColor(index, dark))),
            'lines 0–7 are base colours: no role is read for them',
        ).toEqual([]);
        expect(
            rolesReadBy(() => growthBrokerColor(8, dark)),
            'line 8, the first shade: its default poles read the card, once',
        ).toEqual(['--lf-surface-card']);
        expect(
            rolesReadBy(() => growthBrokerColor(8, dark, shadePoles(dark, DARK_CARD))),
            'poles given: the page’s card is not read',
        ).toEqual([]);
    });

    it('follows a Designer Lab edit (C3): read through categoryColor at each call, never kept from an earlier one', () => {
        // The hook harness of section 5: `publishHook` and `EDITED`. Line 1 is ETF; line 9, ETF one shade on.
        expect(same(growthBrokerColor(1, false)), 'barrier: before the edit, the table value').toBe('#1D5BD8');

        vi.stubGlobal('__LF_DESIGNER_LAB__', true);
        const hook = publishHook((kind, key) => (kind === 'type' && key === 'ETF' ? EDITED : null));

        expect(growthBrokerColor(1, false)).toBe(EDITED);
        expect(hook).toHaveBeenLastCalledWith('type', 'ETF', false);
        const editedShade = familyShade(EDITED, 1, shadePoles(true, DARK_CARD));
        expect(same(editedShade), 'barrier: the first shade of the edit is not the edit itself').not.toBe(same(EDITED));
        expect(growthBrokerColor(9, true), 'line 9, the same type one shade on, dark theme: the edit reaches the shaded line too').toBe(editedShade);
        expect(same(growthBrokerColor(0, false)), 'a line the edit leaves alone keeps its table value').toBe('#6D28D9');
    });
});

// =============================================================================
// 5. C3 — the Designer Lab's hook: in debug it answers first, in release it is gone
// =============================================================================

type Answer = (kind: CategoryKind, key: string, dark: boolean) => string | null | undefined;

/** Publishes a Lab hook answering `answer`, as the Lab client does on `window.__lfDesignerLab`, and returns its spy. */
function publishHook(answer: Answer) {
    const categoryColorSpy = vi.fn(answer);
    vi.stubGlobal('__lfDesignerLab', {categoryColor: categoryColorSpy});
    return categoryColorSpy;
}

const EDITED = '#123456';

describe('C3 in a debug build — the Lab answers first', () => {
    it('hands out the edited colour, for categoryColor and for rank 0 of a sequence, and asks with the caller’s own arguments', () => {
        vi.stubGlobal('__LF_DESIGNER_LAB__', true);
        const hook = publishHook((kind, key) => (kind === 'type' && key === 'ETF' ? EDITED : null));
        const poles = shadePoles(false, DARK_CARD);

        expect(categoryColor('type', 'ETF', false)).toBe(EDITED);
        expect(hook).toHaveBeenLastCalledWith('type', 'ETF', false);
        expect(sequenceColor('type', ['ETF', 'BOND'], 0, false, poles)).toBe(EDITED);
        expect(sequenceColor('type', ['ETF', 'BOND'], 2, false, poles), 'a shade follows the edit (C1): it is derived from the colour returned').toBe(familyShade(EDITED, 1, poles));

        expect(same(categoryColor('type', 'BOND', true)), 'a key the hook leaves alone keeps its table value').toBe('#22D3EE');
        expect(hook).toHaveBeenLastCalledWith('type', 'BOND', true);
    });

    it.each([
        ['null', null],
        ['undefined', undefined],
        ['an empty string', ''],
    ] as const)('keeps the table value when the hook answers %s', (_what, answer) => {
        vi.stubGlobal('__LF_DESIGNER_LAB__', true);
        const hook = publishHook(() => answer);

        expect(same(categoryColor('sector', 'Technology', false))).toBe('#1D5BD8');
        expect(hook, 'barrier: the hook was asked').toHaveBeenCalledTimes(1);
    });

    it('keeps the table value when no hook is published, or the hook has no categoryColor', () => {
        vi.stubGlobal('__LF_DESIGNER_LAB__', true);
        vi.stubGlobal('__lfDesignerLab', undefined);
        expect(same(categoryColor('sector', 'Technology', false)), 'no hook').toBe('#1D5BD8');

        vi.stubGlobal('__lfDesignerLab', {active: () => true});
        expect(same(categoryColor('sector', 'Technology', false)), 'a hook without categoryColor').toBe('#1D5BD8');
    });

    it.each([
        ['false', false],
        ['undefined', undefined],
    ] as const)('ignores a published hook, never asking it, when __LF_DESIGNER_LAB__ is %s', (_what, flag) => {
        vi.stubGlobal('__LF_DESIGNER_LAB__', flag);
        const hook = publishHook(() => EDITED);

        expect(same(categoryColor('type', 'ETF', false))).toBe('#1D5BD8');
        expect(same(sequenceColor('type', CATEGORY_SEQUENCE, 1, false, shadePoles(false, DARK_CARD)))).toBe('#1D5BD8');
        expect(hook).not.toHaveBeenCalled();
    });

    it('ignores a published hook when the define is absent altogether, as under Vitest', () => {
        const hook = publishHook(() => EDITED);
        expect(typeof __LF_DESIGNER_LAB__, 'premise: no define').toBe('undefined');

        expect(same(categoryColor('type', 'ETF', true))).toBe('#60A5FA');
        expect(hook).not.toHaveBeenCalled();
    });
});

/** What this test needs of esbuild's API. */
interface Esbuild {
    version: string;
    transform(source: string, options: {define: Record<string, string>; minify: boolean; loader: 'ts'; format: 'esm'}): Promise<{code: string}>;
}

/**
 * The esbuild the release build minifies with — vite's own dependency (`build.minify: 'esbuild'` in vite.config.ts) —
 * loaded directly. Not through the bare `esbuild` specifier: in this tree it resolves another copy, a dependency of
 * svelte-i18n hoisted to the top of node_modules, which the frontend does not declare and vite does not run.
 */
function releaseEsbuild(): Esbuild {
    const vitePackage = createRequire(import.meta.url).resolve('vite/package.json');
    return createRequire(vitePackage)('esbuild') as Esbuild;
}

describe('C3 in a release build — the minifier drops the hook', () => {
    it('leaves no trace of the Lab once __LF_DESIGNER_LAB__ is false, and keeps the hook when it is true', async () => {
        const esbuild = releaseEsbuild();
        const source = read(CHART_CATEGORIES_TS);
        const build = (flag: 'false' | 'true') => esbuild.transform(source, {define: {__LF_DESIGNER_LAB__: flag}, minify: true, loader: 'ts', format: 'esm'});
        const [release, debug] = await Promise.all([build('false'), build('true')]);

        for (const [name, output] of [
            ['release', release],
            ['debug', debug],
        ] as const) {
            // Barriers: each output is the module, minified, with the define applied — not an empty or failed transform.
            expect(output.code, `${name} (esbuild ${esbuild.version}): the module's exports`).toMatch(/export\s*\{[^}]*\bcategoryColor\b/);
            expect(output.code, `${name}: the designer's values`).toContain('#6D28D9');
            expect(output.code, `${name}: the define was replaced`).not.toContain('__LF_DESIGNER_LAB__');
        }
        expect(release.code, `release (esbuild ${esbuild.version}): the hook's branch survived the minifier`).not.toContain('__lfDesignerLab');
        expect(debug.code, 'positive control: with the flag on, the hook is in the output').toContain('__lfDesignerLab');
    });
});

// =============================================================================
// 6. Key coverage against the backend
// =============================================================================

/**
 * The anti-vacuous guard: every check below loops over a scraped collection, so an empty or partial scrape has to fail
 * here, naming its source, instead of turning the checks into no-ops that pass. (After `assertScraped` in
 * `src/lib/utils/__tests__/assetTypeTables.test.ts`, copied rather than imported: importing a test file registers its
 * tests twice.)
 */
function assertScraped(what: string, values: readonly string[], anchors: readonly string[]): void {
    expect(values.length, `${what}: the scrape returned nothing. The pattern no longer matches the source — every assertion built on this list would pass without checking anything.`).toBeGreaterThan(0);
    const missing = anchors.filter((anchor) => !values.includes(anchor));
    expect(missing, `${what}: the scrape is missing values that are certainly present (${anchors.join(', ')}), so it read the source only in part.`).toEqual([]);
}

/** The body of a Python class: from its header to the next line that starts at the first column. */
function classBody(source: string, header: string, file: string): string {
    const start = source.indexOf(header);
    expect(start, `${file} no longer declares "${header}": this test cannot find the enum it is built on.`).toBeGreaterThan(-1);
    const rest = source.slice(start + header.length);
    const end = rest.search(/\n(?=\S)/);
    return end === -1 ? rest : rest.slice(0, end);
}

/** `FinancialSector`'s values, from `backend/app/utils/asset/sector.py`: the members of the class body, not its aliases. */
function readFinancialSectors(): string[] {
    const body = classBody(read(SECTOR_PY), 'class FinancialSector(StrEnum):', 'sector.py');
    const values = [...body.matchAll(/^ {4}[A-Z][A-Z0-9_]*\s*=\s*"([^"]+)"/gm)].map((match) => match[1]);
    assertScraped('FinancialSector (backend/app/utils/asset/sector.py)', values, ['Industrials', 'Health Care', 'Government Bonds', 'Other']);
    return values;
}

/** The engine's buckets, `ALLOCATION_BUCKETS` in sector.py, each name resolved to its string. */
function readAllocationBuckets(): string[] {
    const source = read(SECTOR_PY);
    const tuple = /^ALLOCATION_BUCKETS\b[^=]*=\s*\(([^)]*)\)/m.exec(source);
    expect(tuple, 'sector.py no longer declares ALLOCATION_BUCKETS as a tuple of names').not.toBeNull();
    const names = tuple![1]
        .split(',')
        .map((name) => name.trim())
        .filter((name) => name !== '');
    const values = names.map((name) => new RegExp(`^${name}\\s*=\\s*"([^"]+)"`, 'm').exec(source)?.[1] ?? `<${name} unresolved>`);
    assertScraped('ALLOCATION_BUCKETS (backend/app/utils/asset/sector.py)', values, ['Liquidity', 'Unknown']);
    return values;
}

/** `AssetType`'s values, from `backend/app/db/models.py` (the scrape of `allocationTypeEmoji.test.ts`, copied). */
function readAssetTypes(): string[] {
    const source = read(MODELS_PY);
    const start = source.indexOf('class AssetType(StrEnum):');
    expect(start, 'backend/app/db/models.py no longer declares "class AssetType(StrEnum)": this test cannot find the enum it is built on.').toBeGreaterThan(-1);
    const rest = source.slice(start);
    const nextClass = rest.search(/\nclass\s+\w+/);
    const body = nextClass === -1 ? rest : rest.slice(0, nextClass);
    const values = [...body.matchAll(/^ {4}[A-Z][A-Z0-9_]*\s*=\s*["']([A-Z0-9_]+)["']/gm)].map((match) => match[1]);
    assertScraped('AssetType (backend/app/db/models.py)', values, ['STOCK', 'ETF', 'OTHER', 'ETF_STOCK', 'ETF_MONETARY', 'CROWDFUND_REAL_ESTATE']);
    return values;
}

/**
 * `ASSET_TYPE_FAMILY` (subtype → family) of `src/lib/utils/assetTypes.ts`, read as text: importing the module would
 * drag in the generated API client, which is gitignored. `assetTypeFamily` reads this map, and a type it does not list
 * is its own family.
 */
function readAssetTypeFamily(): Map<string, string> {
    const what = 'ASSET_TYPE_FAMILY (src/lib/utils/assetTypes.ts)';
    const source = read(ASSET_TYPES_TS);
    const declarations = [...source.matchAll(/(?:export\s+)?const\s+ASSET_TYPE_FAMILY\s*:[^=]*=\s*\{/g)];
    expect(declarations.length, `${what}: expected exactly one declaration, found ${declarations.length}`).toBe(1);
    const start = declarations[0].index! + declarations[0][0].length;
    const end = source.indexOf('};', start);
    expect(end, `${what}: the object literal is never closed with "};"`).toBeGreaterThan(start);
    const body = source.slice(start, end);
    const keys = [...body.matchAll(/^\s*([A-Z][A-Z0-9_]*)\s*:/gm)].map((match) => match[1]);
    const entries = [...body.matchAll(/^\s*([A-Z][A-Z0-9_]*)\s*:\s*'([A-Z][A-Z0-9_]*)'/gm)].map((match) => [match[1], match[2]] as const);
    assertScraped(what, keys, ['ETF_STOCK', 'ETF_MONETARY', 'CROWDFUND_REAL_ESTATE']);
    expect(
        entries.map(([key]) => key),
        `${what}: an entry is not a plain single-quoted family, so it would drop out of the checks`,
    ).toEqual(keys);
    return new Map(entries);
}

describe('key coverage against the backend — every key the engine can send has its colour', () => {
    it('reads the sources it is built on: the enums, the buckets and the family map, each scrape guarded', () => {
        // Every case below loops over these scrapes; each helper fails here, naming its source, if it reads nothing.
        readFinancialSectors();
        readAllocationBuckets();
        readAssetTypes();
        const family = readAssetTypeFamily();
        expect(family.get('ETF_STOCK')).toBe('ETF');
        expect(family.get('CROWDFUND_REAL_ESTATE')).toBe('CROWDFUND');
    });

    it('gives every FinancialSector value a sector colour of its own, in both themes', () => {
        const gaps = readFinancialSectors().flatMap((sector) => {
            const reasons: string[] = [];
            if (!CATEGORY_KEYS.sector.includes(sector)) reasons.push(`${sector}: not a key of the sector table`);
            for (const dark of THEMES) {
                if (same(categoryColor('sector', sector, dark)) === same(UNCLASSIFIED[themeName(dark)])) reasons.push(`${sector}: reads unclassified in the ${themeName(dark)} theme`);
            }
            return reasons;
        });
        expect(gaps, 'a sector the backend can send has no colour of its own: it would be drawn as unclassified').toEqual([]);
    });

    it('keys the sector table by FinancialSector values only', () => {
        const sectors = readFinancialSectors();
        expect(
            CATEGORY_KEYS.sector.filter((key) => !sectors.includes(key)),
            'these sector keys are not FinancialSector values: dead entries, or a rename that stopped halfway',
        ).toEqual([]);
    });

    it('gives every AssetType value, resolved to its family, a type colour of its own, in both themes', () => {
        const family = readAssetTypeFamily();
        const gaps = readAssetTypes().flatMap((type) => {
            const resolved = family.get(type) ?? type;
            const reasons: string[] = [];
            if (!CATEGORY_KEYS.type.includes(resolved)) reasons.push(`${type} → ${resolved}: not a key of the type table`);
            for (const dark of THEMES) {
                if (same(categoryColor('type', resolved, dark)) === same(UNCLASSIFIED[themeName(dark)])) reasons.push(`${type} → ${resolved}: reads unclassified in the ${themeName(dark)} theme`);
            }
            return reasons;
        });
        expect(gaps, 'an asset type the backend can send has no colour through its family').toEqual([]);
    });

    it('keys the type table by families only: AssetType values that are no subtype', () => {
        const types = readAssetTypes();
        const family = readAssetTypeFamily();
        expect(
            CATEGORY_KEYS.type.filter((key) => !types.includes(key) || family.has(key)),
            'these type keys are not AssetType values, or are subtypes, which the caller resolves to their family first',
        ).toEqual([]);
    });

    it("names the buckets as the backend does: CATEGORY_BUCKETS is sector.py's ALLOCATION_BUCKETS", () => {
        expect([...CATEGORY_BUCKETS].sort()).toEqual(readAllocationBuckets().sort());
    });
});

// =============================================================================
// 7. GR2 — no semantic red or green; the brand's sage is the cash's alone
// =============================================================================

/** Every category colour the charts can draw: each key of each table and each bucket, in both themes. */
function everyCategoryColour(): Array<{what: string; key: string; colour: string}> {
    return KINDS.flatMap((kind) => [...CATEGORY_KEYS[kind], ...CATEGORY_BUCKETS].flatMap((key) => THEMES.map((dark) => ({what: `${kind} ${key} ${themeName(dark)}`, key, colour: same(categoryColor(kind, key, dark))}))));
}

describe('GR2 — the categories keep out of the semantic colours', () => {
    /** The designer's GR2: the loss and error red, the gain green, light and dark. */
    const SEMANTIC = {'loss red': ['#C82838', '#F84361'], 'gain green': ['#36D399', '#4ADE80']};
    /** GR3: the brand's sage, light and dark, the cash's alone. */
    const SAGE = ['#2D6A54', '#429E79'];

    it('takes neither the loss red nor the gain green, in any table, bucket or theme', () => {
        const colours = everyCategoryColour();
        const expected = KINDS.reduce((sum, kind) => sum + (CATEGORY_KEYS[kind].length + CATEGORY_BUCKETS.length) * THEMES.length, 0);
        expect(colours.length, 'barrier: the check reads every key and bucket of both tables in both themes').toBe(expected);
        const offenders = colours.flatMap(({what, colour}) =>
            Object.entries(SEMANTIC)
                .filter(([, values]) => values.map(same).includes(colour))
                .map(([name]) => `${what} is the ${name} ${colour}`),
        );
        expect(offenders, 'a category is drawn in a semantic colour: its slice would read as a loss or a gain (GR2)').toEqual([]);
    });

    it('keeps the brand’s sage for Liquidity alone', () => {
        const sage = everyCategoryColour().filter(({colour}) => SAGE.map(same).includes(colour));
        expect(sage.length, 'barrier: the cash itself is drawn in the sage').toBeGreaterThan(0);
        expect(
            sage.filter(({key}) => key !== 'Liquidity').map(({what, colour}) => `${what} ${colour}`),
            'a category other than the cash takes the brand’s sage (GR2, GR3)',
        ).toEqual([]);
        expect(sage.map(({what}) => what).sort()).toEqual(['sector Liquidity dark', 'sector Liquidity light', 'type Liquidity dark', 'type Liquidity light']);
    });
});

// =============================================================================
// 8. Distinguishability — ΔE00 ≥ 10 within each table, but the listed pairs
// =============================================================================

describe('the ruler — CIEDE2000, checked against published data before it measures anything', () => {
    it.each(SHARMA_PAIRS)('reproduces pair $pair of Sharma, Wu & Dalal (2005), ΔE00 $deltaE — $branch', ({first, second, deltaE}) => {
        // Both orders: the formula is symmetric, an implementation that reads one hue twice is not.
        expect(Math.abs(ciede2000(first, second) - deltaE), 'first → second').toBeLessThanOrEqual(1e-4);
        expect(Math.abs(ciede2000(second, first) - deltaE), 'second → first').toBeLessThanOrEqual(1e-4);
    });

    it.each(SRGB_LAB)('converts $hex to its published CIELAB (D65) coordinates', ({hex, lab}) => {
        const measured = labOf(hex);
        lab.forEach((expected, axis) => expect(Math.abs(measured[axis] - expected), `${hex} ${['L*', 'a*', 'b*'][axis]}`).toBeLessThanOrEqual(1e-3));
    });

    it('measures nothing it cannot read: a colour that is not #rrggbb throws instead of answering NaN', () => {
        expect(() => deltaE00('#1D5BD8', 'not a colour')).toThrow();
        expect(deltaE00('#1D5BD8', '#1d5bd8'), 'barrier: the case of a hex does not matter').toBe(0);
    });
});

/** Two slices side by side are confused under this distance (`analisi.md` §4). */
const FLOOR = 10;
/** How much closer than its record a listed pair may measure: the record is rounded to one decimal. */
const TOLERANCE = 0.15;

interface ListedPair {
    pair: readonly [string, string];
    /** ΔE00 as the round-2 analysis recorded it, to one decimal. */
    measured: number;
}

/**
 * The pairs `analisi.md` §4 measured under ΔE00 10 on the designer's values, per table and theme — the questions of
 * her round 3. Not corrections: her values stand until she answers. Shorten the list when a pair moves past 10.
 */
const CLOSE_PAIRS: Readonly<Record<string, readonly ListedPair[]>> = {
    'type light': [
        {pair: ['COMMODITY', 'REAL_ESTATE'], measured: 5.0},
        {pair: ['STOCK', 'FUND'], measured: 6.4},
        {pair: ['CRYPTO', 'COMMODITY'], measured: 8.9},
    ],
    'type dark': [
        {pair: ['STOCK', 'FUND'], measured: 7.9},
        {pair: ['COMMODITY', 'REAL_ESTATE'], measured: 9.4},
    ],
    'sector light': [
        {pair: ['Financials', 'Liquidity'], measured: 7.9},
        {pair: ['Consumer Discretionary', 'Telecommunication'], measured: 9.4},
    ],
    'sector dark': [
        {pair: ['Real Estate', 'Energy'], measured: 5.1},
        {pair: ['Consumer Discretionary', 'Telecommunication'], measured: 7.9},
        {pair: ['Technology', 'Government Bonds'], measured: 9.1},
    ],
};

interface Verdict {
    /** How many pairs were measured. */
    pairs: number;
    /** Pairs under the floor that the list does not name. */
    unlisted: string[];
    /** Listed pairs now closer than their record, beyond the rounding. */
    closer: string[];
    /** Listed pairs now at least the floor apart: the list should lose them. */
    apart: string[];
    /** Listed pairs naming a member the table does not have. */
    stale: string[];
}

const pairId = (first: string, second: string): string => [first, second].sort().join(' · ');

/** Every pair of `members` (`[key, colour]`), measured, and judged against `listed`. */
function distinguishability(members: ReadonlyArray<readonly [string, string]>, listed: readonly ListedPair[]): Verdict {
    const records = new Map(listed.map((entry) => [pairId(...entry.pair), entry]));
    const verdict: Verdict = {pairs: 0, unlisted: [], closer: [], apart: [], stale: []};
    const keys = new Set(members.map(([key]) => key));
    for (const {pair} of listed) if (!pair.every((key) => keys.has(key))) verdict.stale.push(pair.join(' · '));

    members.forEach(([firstKey, firstColour], i) => {
        members.slice(i + 1).forEach(([secondKey, secondColour]) => {
            verdict.pairs += 1;
            const distance = deltaE00(firstColour, secondColour);
            const record = records.get(pairId(firstKey, secondKey));
            const shown = `${firstKey} ${firstColour} · ${secondKey} ${secondColour}: ΔE00 ${distance.toFixed(2)}`;
            if (!record) {
                if (distance < FLOOR) verdict.unlisted.push(shown);
            } else if (distance >= FLOOR) {
                verdict.apart.push(shown);
            } else if (distance < record.measured - TOLERANCE) {
                verdict.closer.push(`${shown}, recorded ${record.measured.toFixed(1)}`);
            }
        });
    });
    return verdict;
}

describe('distinguishability — every pair of a table at least ΔE00 10 apart, but the pairs listed for round 3', () => {
    const TABLE_THEMES = KINDS.flatMap((kind) => THEMES.map((dark) => [`${kind} ${themeName(dark)}`, kind, dark] as const));

    it.each(TABLE_THEMES)('%s, the two buckets included', (name, kind, dark) => {
        const members = [...CATEGORY_KEYS[kind], ...CATEGORY_BUCKETS].map((key) => [key, categoryColor(kind, key, dark)] as const);
        const listed = CLOSE_PAIRS[name] ?? [];
        const verdict = distinguishability(members, listed);

        expect(verdict.pairs, 'barrier: every pair of the table was measured').toBe((members.length * (members.length - 1)) / 2);
        expect(verdict.stale, `the list for ${name} names a key the table does not have: fix the list`).toEqual([]);
        expect(verdict.unlisted, `these pairs of ${name} are closer than ΔE00 ${FLOOR}, and not on the list the designer's round 3 starts from (analisi.md §4): a slice next to the other would be confused with it`).toEqual([]);
        expect(verdict.closer, `these listed pairs of ${name} are now closer than the analysis recorded them: the values moved, toward each other`).toEqual([]);
        expect(verdict.apart, `these listed pairs of ${name} are now at least ΔE00 ${FLOOR} apart: shorten CLOSE_PAIRS, and the round-3 list with it`).toEqual([]);
    });

    it('lists exactly the ten pairs of analisi.md §4', () => {
        expect(Object.values(CLOSE_PAIRS).flat().length).toBe(10);
        expect(Object.keys(CLOSE_PAIRS).sort()).toEqual(TABLE_THEMES.map(([name]) => name).sort());
    });

    it('the gate fails on what it guards against: an unlisted close pair, a listed pair closer than recorded, one now apart, one stale', () => {
        const members = [
            ['A', '#ff0000'],
            ['B', '#fe0000'],
            ['C', '#0000ff'],
            ['D', '#ff0100'],
        ] as const;
        const verdict = distinguishability(members, [
            {pair: ['B', 'D'], measured: 5.0},
            {pair: ['A', 'C'], measured: 9.0},
            {pair: ['A', 'Z'], measured: 1.0},
        ]);

        expect(verdict.pairs).toBe(6);
        expect(verdict.unlisted.map((line) => line.split(':')[0])).toEqual(['A #ff0000 · B #fe0000', 'A #ff0000 · D #ff0100']);
        expect(verdict.closer.map((line) => line.split(':')[0])).toEqual(['B #fe0000 · D #ff0100']);
        expect(verdict.apart.map((line) => line.split(':')[0])).toEqual(['A #ff0000 · C #0000ff']);
        expect(verdict.stale).toEqual(['A · Z']);
    });
});
