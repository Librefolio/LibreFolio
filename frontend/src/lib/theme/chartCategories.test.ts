/**
 * chartCategories — the fixed colour of every category the charts draw (DV: the designer's round 3, her final palette,
 * on the rules of her round 2, GR1–GR5, D-T17), and the contract with the Designer Lab (C1–C3).
 *
 * What is pinned, one concern per block:
 *
 * 1. **The designer's values.** Every key of both tables and the two buckets, both themes, read through
 *    `categoryColor`, against her tables as transcribed below from §1.2 and §1.3 of `decisioni.md` — the values to write
 *    in the code, her choices on the options sheet included; `palette-finale.json` beside it holds the same — in
 *    `LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/designer-feedback/2026-10-17-round3-grafici/`. The
 *    lookup ignores case, spaces and underscores — `lookupKey`, exported so the Designer Lab keys its edits the same
 *    way; a key outside the tables — an unresolved subtype included — reads as unclassified.
 * 2. **C1, one read point.** The module exports exactly what its header documents, and no colour at any depth: the
 *    tables cannot be read past the hook, and the sequences hold references to categories, never colours.
 * 3. **C2, one literal per line.** Every colour of the file sits alone on a `light:`/`dark:` line, and those lines are
 *    the colours `categoryColor` returns for the sectors and «Unknown»: the Lab exports an edit by file and line. The
 *    asset types and the cash have no line since DV-11: they are the roles `CATEGORY_ROLES` names.
 * 4. **The sequences (GR5, §1.4, §1.5).** `CATEGORY_SEQUENCE` is the first eight types of her table; `COUNTRY_SEQUENCE`
 *    fourteen references to the two tables whose colours are her §1.4 table — the type, where a type and a sector
 *    share a colour. A sequence in order, then one shade further at each round: 98 distinct colours for the 14
 *    countries. The Growth chart's broker lines are the first eight types the same way, 56 distinct colours (DV-8), the
 *    shades toward the poles the chart passes or else the page's card, read only from the ninth line on; read at each
 *    draw so a Designer Lab edit reaches them (`growthBrokerColor`, TD-1b).
 * 5. **C3, the hook.** In a debug build the Lab answers first, asked with each reference's own kind and key; a null
 *    answer, a missing hook or the flag off leave the table's value. In a release build the hook is gone: the esbuild
 *    the release build minifies with, run on this source with the define a release build sets, leaves no trace of it.
 * 6. **Key coverage against the backend.** Every `FinancialSector` value has a sector colour and every sector key is
 *    one; every `AssetType` value, resolved to its family, has a type colour and every type key is a family; the
 *    buckets are the backend's. Scraped as text, each scrape guarded against reading nothing.
 * 7. **The rulers.** CIEDE2000 and OKLCH (`$test/colorDistance`), each proven on published data — Sharma, Wu & Dalal's
 *    pairs and Lindbloom's CIELAB; Ottosson's OKLab table and the OKLCH of CSS Color 4 — before a gate reads it.
 * 8. **§1.1, the rule of the greens.** Every colour a category is drawn in — both tables, both buckets, the fourteen
 *    countries, both themes — is out of the OKLCH green band (115°–225° at a chroma over 0.03), at least ΔE00 10 from
 *    the success green of its theme and never its danger red, and at least 3:1 on its card (WCAG 1.4.11). The roles are
 *    tokens.css's, read with the colour gate's own resolver (`scripts/theme/theme-roles.mjs`).
 * 9. **Distinguishability (§1.8).** No two colours of one table under ΔE00 5, with no exception possible; under 8, only
 *    the pairs the designer kept, each named with its measure, so a pair that moves either way is seen. **The two
 *    buckets join both tables**: the engine draws the cash and the unclassified beside the types and beside the sectors
 *    alike. **«Unknown» joins the countries**: the geography history draws the unclassified beside them.
 * 10. **Parity with T's category roles (§1.9, decision A).** The badges are HTML and read classes, so the type colours
 *     are also `--lf-cat-*` roles of tokens.css (T). Since `CATEGORY_ROLES_IN_TOKENS` was flipped (18/10/2026), each
 *     must be `categoryColor` of its key, in both themes.
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

import {contrastRatio, parseTokens, readTokens, resolveColour, TOKEN_BLOCKS, tokenValue, toHex} from '../../../scripts/theme/theme-roles.mjs';
import {ciede2000, deltaE00, labOf, OKLAB_XYZ, oklabOfXyz, oklchOf, SHARMA_PAIRS, SRGB_LAB, SRGB_OKLCH} from '$test/colorDistance';

import {CATEGORY_BUCKETS, CATEGORY_KEYS, CATEGORY_ROLES, CATEGORY_SEQUENCE, categoryColor, type CategoryKind, type CategoryRef, COUNTRY_SEQUENCE, isUnclassifiedCountry, lookupKey, sequenceColor} from './chartCategories';
import {growthBrokerColor} from './chartPalettes';
import {familyShade, shadePoles} from './chartShades';
import {setRoleReader} from './roleColors';

// =============================================================================
// The designer's tables (round 3), as she wrote them: key, light, dark
// =============================================================================

type Row = readonly [key: string, light: string, dark: string];

/** §1.2, «Tipi di asset»: the asset-type families, in her order. Her last row, `Liquidity`, is the bucket's, below. */
const DESIGNER_TYPES: readonly Row[] = [
    ['STOCK', '#7041C6', '#B69AF0'],
    ['ETF', '#2459B8', '#82ACF8'],
    ['BOND', '#536A9E', '#9BAED8'],
    ['CRYPTO', '#B87916', '#E8BD69'],
    ['FUND', '#5147B8', '#9280FF'],
    ['HOLD', '#5D687B', '#C6D0E0'],
    ['CROWDFUND', '#8B547D', '#D5A0C7'],
    ['COMMODITY', '#B85E45', '#E99A82'],
    ['REAL_ESTATE', '#96602C', '#D6A36C'],
    ['INDEX', '#A33D79', '#E58BB9'],
    ['OTHER', '#727B87', '#A9B0BB'],
];

/** §1.3, «Settori»: the sectors, in her order. Her last two rows, `Liquidity` and `Unknown`, are the buckets', below. */
const DESIGNER_SECTORS: readonly Row[] = [
    ['Industrials', '#586579', '#ACC6DA'],
    ['Technology', '#2459B8', '#82ACF8'],
    ['Financials', '#6748A8', '#B9A0EB'],
    ['Consumer Discretionary', '#8B4F9D', '#D2A0E0'],
    ['Health Care', '#2878A8', '#7CC0E8'],
    ['Real Estate', '#A45D2A', '#DDA16F'],
    ['Basic Materials', '#A84C36', '#E18E7B'],
    ['Energy', '#B27A16', '#E7BD69'],
    ['Consumer Staples', '#8B647A', '#C6A2B6'],
    ['Telecommunication', '#5147B8', '#9280FF'],
    ['Utilities', '#526F9A', '#9CB8E3'],
    ['Corporate Bonds', '#993D79', '#E58BB9'],
    ['Government Bonds', '#263F78', '#7A93CB'],
    ['Other', '#727B87', '#A9B0BB'],
];

/**
 * The engine's two buckets, beside both tables: the cash, a slate blue (the `Liquidity` row of §1.2 and of §1.3, one
 * colour in both), and the unclassified, a blue-grey (the `Unknown` row of §1.3).
 */
const DESIGNER_BUCKETS: readonly Row[] = [
    ['Liquidity', '#3F628C', '#639BC0'],
    ['Unknown', '#718C9F', '#83939D'],
];

/** §1.4, the countries of the geography history: fourteen colours, position by position, in the same order in both themes. */
const DESIGNER_COUNTRIES: ReadonlyArray<readonly [light: string, dark: string]> = [
    ['#2459B8', '#82ACF8'],
    ['#7041C6', '#B69AF0'],
    ['#A84C36', '#E18E7B'],
    ['#B27A16', '#E7BD69'],
    ['#2878A8', '#7CC0E8'],
    ['#993D79', '#E58BB9'],
    ['#526F9A', '#9CB8E3'],
    ['#8B4F9D', '#D2A0E0'],
    ['#A45D2A', '#DDA16F'],
    ['#5147B8', '#9280FF'],
    ['#5D687B', '#C6D0E0'],
    ['#8B647A', '#C6A2B6'],
    ['#263F78', '#7A93CB'],
    ['#727B87', '#A9B0BB'],
];

const KINDS: readonly CategoryKind[] = ['type', 'sector'];
const THEMES = [false, true] as const;
const themeName = (dark: boolean): 'light' | 'dark' => (dark ? 'dark' : 'light');
/** The two themes as `it.each` rows: a name for the title, the flag for the call. */
const THEME_CASES = THEMES.map((dark) => [themeName(dark), dark] as const);
const DESIGNER: Readonly<Record<CategoryKind, readonly Row[]>> = {type: DESIGNER_TYPES, sector: DESIGNER_SECTORS};

/** Her value for `key` of `kind`, the buckets included: what the cases below expect, never a hex copied into them. */
function designerValue(kind: CategoryKind, key: string, dark: boolean): string {
    const row = [...DESIGNER[kind], ...DESIGNER_BUCKETS].find(([candidate]) => candidate === key);
    if (!row) throw new Error(`${kind} ${key} is not a row of the designer's tables`);
    return dark ? row[2] : row[1];
}

/** The unclassified colour, §1.3's `Unknown`: what any key outside the tables reads as. */
const UNCLASSIFIED = {light: designerValue('sector', 'Unknown', false), dark: designerValue('sector', 'Unknown', true)} as const;

/** Two colours alike, whatever the letter case of their hex. */
const same = (colour: string) => colour.toUpperCase();

/** tokens.css, parsed by the colour gate's own module, as the gates read it. */
const TOKENS = readTokens();

/** A role of tokens.css in a theme, as `#rrggbb`, resolved by the colour gate's own resolver. */
function tokenColour(role: string, dark: boolean): string {
    return toHex(resolveColour(TOKENS, `var(${role})`, themeName(dark)));
}

/**
 * The dark theme's card (`--lf-surface-card`), as tokens.css resolves it: the near pole of the dark shades. Without a
 * page the charts read its stand-in, which `roleColors.test.ts` holds to the same value.
 */
const DARK_CARD = tokenColour('--lf-surface-card', true);

afterEach(() => {
    vi.unstubAllGlobals();
});

// =============================================================================
// 1. The designer's values, through the one read point
// =============================================================================

describe("categoryColor — the designer's values (round 3, §1.2 and §1.3), both themes", () => {
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

/** What the module's header documents, the types aside (`CategoryKind` and `CategoryRef` are erased). */
const DOCUMENTED_EXPORTS = ['CATEGORY_BUCKETS', 'CATEGORY_KEYS', 'CATEGORY_ROLES', 'CATEGORY_SEQUENCE', 'COUNTRY_SEQUENCE', 'categoryColor', 'isUnclassifiedCountry', 'lookupKey', 'sequenceColor'];

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

    it('exports no colour and no light/dark pair, at any depth: its lists hold keys, its sequences references to them', () => {
        expect(
            [CATEGORY_SEQUENCE, COUNTRY_SEQUENCE].map((sequence) => sequence.length),
            'barrier: the walk has references to go through',
        ).toEqual([8, 14]);
        expect(Object.entries(NAMESPACE).flatMap(([name, value]) => colourLeaks(value, name))).toEqual([]);
    });

    it('positive control: the walk names a table, and its colours, where one is exported — and a colour where a reference names a key', () => {
        const leaky = {
            TABLE: {ETF: {light: '#2459B8', dark: '#82ACF8'}},
            LIST: ['STOCK', 'rgb(1, 2, 3)'],
            SEQUENCE: [
                {kind: 'type', key: 'ETF'},
                {kind: 'type', key: '#2459B8'},
            ],
        };
        expect(colourLeaks(leaky, 'leaky')).toEqual(['leaky.TABLE.ETF (a light/dark pair)', 'leaky.TABLE.ETF.light', 'leaky.TABLE.ETF.dark', 'leaky.LIST.1', 'leaky.SEQUENCE.1.key']);
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
    it('sets every colour of the file alone on a `light:` or `dark:` line, one line per sector and for «Unknown»', () => {
        const source = read(CHART_CATEGORIES_TS);
        const literalLines = source
            .split('\n')
            .map((line) => /^\s*(light|dark): '(#[0-9A-Fa-f]{6})',$/.exec(line))
            .filter((match) => match !== null);
        const everyHex = source.match(/#[0-9A-Fa-f]{6}\b/g) ?? [];

        expect(literalLines.length, 'barrier: the scan finds the literal lines').toBeGreaterThan(0);
        expect(everyHex.length, 'a colour of the file sits elsewhere than alone on its own light:/dark: line — inline in a pair, in an expression, in a comment').toBe(literalLines.length);

        for (const dark of THEMES) {
            const theme = themeName(dark);
            const onLines = literalLines.filter((match) => match[1] === theme).map((match) => same(match[2]));
            const returned = [...CATEGORY_KEYS.sector.map((key) => categoryColor('sector', key, dark)), categoryColor('sector', 'Unknown', dark)].map(same);
            expect(onLines.length, `${theme}: one line per sector and one for «Unknown»`).toBe(CATEGORY_KEYS.sector.length + 1);
            expect([...onLines].sort(), `${theme}: the lines hold exactly the colours categoryColor returns`).toEqual([...returned].sort());
        }
    });

    it('draws each asset type and the cash in its role (DV-11): one per type of the table and the cash, the role read where the page shows the theme', () => {
        expect(CATEGORY_ROLES.map((c) => c.key)).toEqual([...CATEGORY_KEYS.type, 'Liquidity']);
        expect(CATEGORY_ROLES.map((c) => c.target)).toEqual([...CATEGORY_KEYS.type.map((key) => `type:${key}`), 'bucket:Liquidity']);
        expect(
            CATEGORY_ROLES.filter(({key, role}) => role !== `--lf-cat-${key.toLowerCase().replace(/_/g, '-')}`).map(({role}) => role),
            'the role is the key lower-cased, `_` → `-`',
        ).toEqual([]);

        const read: string[] = [];
        setRoleReader((role) => {
            read.push(role);
            return '#123456';
        });
        for (const kind of KINDS) expect(categoryColor(kind, 'Liquidity', false), `${kind}: the cash is its role in both kinds`).toBe('#123456');
        expect(categoryColor('type', 'ETF', true)).toBe('#123456');
        expect(categoryColor('sector', 'Technology', false), 'a sector is a line of the file, no role').not.toBe('#123456');
        expect(read).toEqual(['--lf-cat-liquidity', '--lf-cat-liquidity', '--lf-cat-etf']);
        setRoleReader(null);
    });

    it('reads the role on the chart’s own element when it is given one, as chartRoles does; a sector reads nothing', () => {
        const element = {nodeName: 'DIV'} as unknown as Element;
        const scopes: Array<Element | null> = [];
        setRoleReader((_role, scope) => {
            scopes.push(scope);
            return scope === element ? '#654321' : '';
        });
        expect(categoryColor('type', 'ETF', false, element)).toBe('#654321');
        expect(sequenceColor(CATEGORY_SEQUENCE, 1, true, shadePoles(true, '#151b19'), element), 'a sequence passes the element on').toBe('#654321');
        expect(categoryColor('sector', 'Technology', false, element)).not.toBe('#654321');
        expect(scopes).toEqual([element, element]);
        setRoleReader(null);
    });
});

// =============================================================================
// 4. The sequences (GR5, §1.4, §1.5) and the Growth chart's broker lines
// =============================================================================

/** A reference as the messages name it: `sector Health Care`. */
const refName = ({kind, key}: CategoryRef): string => `${kind} ${key}`;

/** The base colour a reference reads, through the one read point. */
const refColour = ({kind, key}: CategoryRef, dark: boolean): string => categoryColor(kind, key, dark);

/** Both colours of a category, `LIGHT DARK`, as `same` reads them: what "the same colour" means across the two themes. */
const colourPair = (kind: CategoryKind, key: string): string => THEMES.map((dark) => same(categoryColor(kind, key, dark))).join(' ');

describe('the sequences — categories by reference, read through categoryColor (§1.4, §1.5)', () => {
    it('CATEGORY_SEQUENCE is the first eight types of her table, in her order, as type references (§1.5)', () => {
        const eight = ['STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND', 'HOLD', 'CROWDFUND', 'COMMODITY'];
        expect(CATEGORY_SEQUENCE).toEqual(eight.map((key) => ({kind: 'type', key})));
        expect(CATEGORY_SEQUENCE.map(({key}) => key)).toEqual(CATEGORY_KEYS.type.slice(0, CATEGORY_SEQUENCE.length));
    });

    it.each(THEME_CASES)('%s: COUNTRY_SEQUENCE, read through categoryColor, is her §1.4 table, position by position', (_theme, dark) => {
        expect(COUNTRY_SEQUENCE).toHaveLength(DESIGNER_COUNTRIES.length);
        expect(COUNTRY_SEQUENCE.map((ref) => same(refColour(ref, dark)))).toEqual(DESIGNER_COUNTRIES.map(([light, darkColour]) => same(dark ? darkColour : light)));
    });

    it('names in every reference a key of its own table — no bucket, nothing that reads unclassified', () => {
        const sequences = {CATEGORY_SEQUENCE, COUNTRY_SEQUENCE};
        const problems = Object.entries(sequences).flatMap(([name, sequence]) =>
            sequence.flatMap((ref, index) => {
                const at = `${name}[${index}], ${refName(ref)}`;
                if (!KINDS.includes(ref.kind)) return [`${at}: no table of that kind`];
                if (!CATEGORY_KEYS[ref.kind].includes(ref.key)) return [`${at}: not a key of the ${ref.kind} table`];
                return THEMES.filter((dark) => same(refColour(ref, dark)) === same(UNCLASSIFIED[themeName(dark)])).map((dark) => `${at}: reads unclassified in the ${themeName(dark)} theme`);
            }),
        );
        expect(new Set(COUNTRY_SEQUENCE.map(({kind}) => kind)), 'barrier: the countries draw on both tables, so both are checked').toEqual(new Set(KINDS));
        expect(problems).toEqual([]);
    });

    it("keeps §1.4's notes: country 10 is the fund, 11 the held asset, 13 the government bonds", () => {
        expect({10: COUNTRY_SEQUENCE[9], 11: COUNTRY_SEQUENCE[10], 13: COUNTRY_SEQUENCE[12]}).toEqual({
            10: {kind: 'type', key: 'FUND'},
            11: {kind: 'type', key: 'HOLD'},
            13: {kind: 'sector', key: 'Government Bonds'},
        });
    });

    it('takes the type where a type and a sector share a colour: countries 1, 10 and 14 are ETF, FUND and OTHER', () => {
        // A country whose colours, in both themes, are those of a type and of a sector refers to the type, so that it
        // follows the type in the Lab (§1.4). Both sides are read: no other country shares a type's colours with a sector.
        const shared = COUNTRY_SEQUENCE.flatMap((ref, index) => {
            const colours = colourPair(ref.kind, ref.key);
            const type = CATEGORY_KEYS.type.find((key) => colourPair('type', key) === colours);
            const sector = CATEGORY_KEYS.sector.find((key) => colourPair('sector', key) === colours);
            return type && sector ? [`country ${index + 1}: ${refName(ref)}, the colours of type ${type} and of sector ${sector}`] : [];
        });
        expect(shared).toEqual(['country 1: type ETF, the colours of type ETF and of sector Technology', 'country 10: type FUND, the colours of type FUND and of sector Telecommunication', 'country 14: type OTHER, the colours of type OTHER and of sector Other']);
    });
});

describe('sequenceColor — a sequence in order, then one shade further at each round (GR5)', () => {
    it.each(THEME_CASES)('%s: the first round is the sequence itself, in order, the base colours unshaded', (_theme, dark) => {
        const poles = shadePoles(dark, DARK_CARD);
        const countries = COUNTRY_SEQUENCE.map((_, rank) => same(sequenceColor(COUNTRY_SEQUENCE, rank, dark, poles)));
        expect(countries).toEqual(DESIGNER_COUNTRIES.map(([light, darkColour]) => same(dark ? darkColour : light)));
        const owners = CATEGORY_SEQUENCE.map((_, rank) => same(sequenceColor(CATEGORY_SEQUENCE, rank, dark, poles)));
        expect(owners).toEqual(DESIGNER_TYPES.slice(0, CATEGORY_SEQUENCE.length).map((row) => same(dark ? row[2] : row[1])));
    });

    it.each(THEME_CASES)('%s: rank 14 of the countries is the first country one shade on, 15 the second, 27 the fourteenth, 28 the first two shades on', (_theme, dark) => {
        const poles = shadePoles(dark, DARK_CARD);
        const base = (index: number) => refColour(COUNTRY_SEQUENCE[index], dark);
        expect(sequenceColor(COUNTRY_SEQUENCE, 14, dark, poles)).toBe(familyShade(base(0), 1, poles));
        expect(sequenceColor(COUNTRY_SEQUENCE, 15, dark, poles)).toBe(familyShade(base(1), 1, poles));
        expect(sequenceColor(COUNTRY_SEQUENCE, 27, dark, poles)).toBe(familyShade(base(13), 1, poles));
        expect(sequenceColor(COUNTRY_SEQUENCE, 28, dark, poles)).toBe(familyShade(base(0), 2, poles));
        expect(same(sequenceColor(COUNTRY_SEQUENCE, 14, dark, poles)), 'barrier: a shade is not its base').not.toBe(same(base(0)));
    });

    it.each(THEME_CASES)('%s: the fourteen countries give 98 distinct colours before they cycle, never a silent repeat', (_theme, dark) => {
        const poles = shadePoles(dark, DARK_CARD);
        const colours = Array.from({length: 99}, (_, rank) => same(sequenceColor(COUNTRY_SEQUENCE, rank, dark, poles)));
        expect(new Set(colours.slice(0, 98)).size).toBe(98);
        expect(colours[98], 'rank 98 starts the cycle again at the first shade').toBe(colours[14]);
    });
});

describe('growthBrokerColor — the Growth chart’s broker lines (GR5, TD-1b, DV-8)', () => {
    /** The designer's colours of her first eight types, in her order, as `same` reads them: the bases of lines 0–7. */
    function designerEight(dark: boolean): string[] {
        return CATEGORY_SEQUENCE.map(({kind, key}) => {
            if (kind !== 'type') throw new Error(`${kind} ${key}: the broker lines take the first eight types`);
            return same(designerValue('type', key, dark));
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
        // The base colours of the types are roles since DV-11: what is measured here is the card the shades read.
        return read.filter((role) => !role.startsWith('--lf-cat-'));
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
        // With no page the card the chart reads is the stand-in of `--lf-surface-card`, tokens.css's DARK_CARD in the dark
        // theme (the parity gate of roleColors.test.ts); the light theme's poles are literals, whatever the card.
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
        expect(lines, 'every line: the sequence of the eight types, on the default poles').toEqual(lines.map((_, index) => sequenceColor(CATEGORY_SEQUENCE, index, dark, poles)));
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
        expect(same(growthBrokerColor(1, false)), 'barrier: before the edit, the table value').toBe(same(designerValue('type', 'ETF', false)));

        vi.stubGlobal('__LF_DESIGNER_LAB__', true);
        const hook = publishHook((kind, key) => (kind === 'type' && key === 'ETF' ? EDITED : null));

        expect(growthBrokerColor(1, false)).toBe(EDITED);
        expect(hook).toHaveBeenLastCalledWith('type', 'ETF', false);
        const editedShade = familyShade(EDITED, 1, shadePoles(true, DARK_CARD));
        expect(same(editedShade), 'barrier: the first shade of the edit is not the edit itself').not.toBe(same(EDITED));
        expect(growthBrokerColor(9, true), 'line 9, the same type one shade on, dark theme: the edit reaches the shaded line too').toBe(editedShade);
        expect(same(growthBrokerColor(0, false)), 'a line the edit leaves alone keeps its table value').toBe(same(designerValue('type', 'STOCK', false)));
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

/** Two type references, as a sequence holds them. */
const ETF_BOND: readonly CategoryRef[] = [
    {kind: 'type', key: 'ETF'},
    {kind: 'type', key: 'BOND'},
];

describe('C3 in a debug build — the Lab answers first', () => {
    it('hands out the edited colour, for categoryColor and for rank 0 of a sequence, and asks with the caller’s own arguments', () => {
        vi.stubGlobal('__LF_DESIGNER_LAB__', true);
        const hook = publishHook((kind, key) => (kind === 'type' && key === 'ETF' ? EDITED : null));
        const poles = shadePoles(false, DARK_CARD);

        expect(categoryColor('type', 'ETF', false)).toBe(EDITED);
        expect(hook).toHaveBeenLastCalledWith('type', 'ETF', false);
        expect(sequenceColor(ETF_BOND, 0, false, poles)).toBe(EDITED);
        expect(sequenceColor(ETF_BOND, 2, false, poles), 'a shade follows the edit (C1): it is derived from the colour returned').toBe(familyShade(EDITED, 1, poles));

        expect(same(categoryColor('type', 'BOND', true)), 'a key the hook leaves alone keeps its table value').toBe(same(designerValue('type', 'BOND', true)));
        expect(hook).toHaveBeenLastCalledWith('type', 'BOND', true);
    });

    it('asks for each country with its reference’s own kind and key: the sequence mixes the two tables', () => {
        vi.stubGlobal('__LF_DESIGNER_LAB__', true);
        const hook = publishHook(() => null);
        const poles = shadePoles(true, DARK_CARD);

        const asked = COUNTRY_SEQUENCE.map((_, rank) => {
            sequenceColor(COUNTRY_SEQUENCE, rank + COUNTRY_SEQUENCE.length, true, poles);
            return hook.mock.lastCall;
        });
        expect(asked, 'the second round, shaded, asks for the same categories as the first').toEqual(COUNTRY_SEQUENCE.map(({kind, key}) => [kind, key, true]));
    });

    it.each([
        ['null', null],
        ['undefined', undefined],
        ['an empty string', ''],
    ] as const)('keeps the table value when the hook answers %s', (_what, answer) => {
        vi.stubGlobal('__LF_DESIGNER_LAB__', true);
        const hook = publishHook(() => answer);

        expect(same(categoryColor('sector', 'Technology', false))).toBe(same(designerValue('sector', 'Technology', false)));
        expect(hook, 'barrier: the hook was asked').toHaveBeenCalledTimes(1);
    });

    it('keeps the table value when no hook is published, or the hook has no categoryColor', () => {
        const technology = same(designerValue('sector', 'Technology', false));
        vi.stubGlobal('__LF_DESIGNER_LAB__', true);
        vi.stubGlobal('__lfDesignerLab', undefined);
        expect(same(categoryColor('sector', 'Technology', false)), 'no hook').toBe(technology);

        vi.stubGlobal('__lfDesignerLab', {active: () => true});
        expect(same(categoryColor('sector', 'Technology', false)), 'a hook without categoryColor').toBe(technology);
    });

    it.each([
        ['false', false],
        ['undefined', undefined],
    ] as const)('ignores a published hook, never asking it, when __LF_DESIGNER_LAB__ is %s', (_what, flag) => {
        vi.stubGlobal('__LF_DESIGNER_LAB__', flag);
        const hook = publishHook(() => EDITED);

        expect(same(categoryColor('type', 'ETF', false))).toBe(same(designerValue('type', 'ETF', false)));
        expect(same(sequenceColor(CATEGORY_SEQUENCE, 1, false, shadePoles(false, DARK_CARD))), 'rank 1 of the owners, ETF').toBe(same(designerValue('type', 'ETF', false)));
        expect(hook).not.toHaveBeenCalled();
    });

    it('ignores a published hook when the define is absent altogether, as under Vitest', () => {
        const hook = publishHook(() => EDITED);
        expect(typeof __LF_DESIGNER_LAB__, 'premise: no define').toBe('undefined');

        expect(same(categoryColor('type', 'ETF', true))).toBe(same(designerValue('type', 'ETF', true)));
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
            expect(output.code, `${name}: the designer's values`).toContain(designerValue('sector', 'Industrials', false));
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
// 7. The rulers — CIEDE2000 and OKLCH, each proven on published data first
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
        expect(() => deltaE00('#2459B8', 'not a colour')).toThrow();
        expect(deltaE00('#2459B8', '#2459b8'), 'barrier: the case of a hex does not matter').toBe(0);
    });
});

/** A published `oklch(L C h)`, each coordinate with one unit of its last published digit: the precision its source gives. */
function publishedOklch(text: string): Array<{value: number; unit: number}> {
    const match = /^oklch\(([\d.]+) ([\d.]+) ([\d.]+)\)$/.exec(text);
    if (!match) throw new Error(`${text} is not oklch(L C h) in numbers`);
    return match.slice(1).map((digits) => ({value: Number(digits), unit: 10 ** -(digits.split('.')[1]?.length ?? 0)}));
}

describe('the hue ruler — OKLCH, checked against published data before it reads a hue', () => {
    it.each(OKLAB_XYZ)("reproduces Ottosson's published pair, XYZ $xyz → OKLab $oklab, to his three decimals", ({xyz, oklab}) => {
        const measured = oklabOfXyz(xyz);
        // Rounded to three decimals: within half a unit of the third.
        oklab.forEach((expected, axis) => expect(Math.abs(measured[axis] - expected), ['L', 'a', 'b'][axis]).toBeLessThanOrEqual(5e-4));
    });

    it.each(SRGB_OKLCH)('reads $what, $hex, as CSS Color 4 writes it: $oklch', ({hex, oklch}) => {
        // Within one unit of the last digit published: the specification's sRGB matrix is not the seven-digit one of
        // `labOf`, and moves the fourth decimal. The sRGB → XYZ step itself is the one `SRGB_LAB` proves above.
        const measured = oklchOf(hex);
        const [L, C, h] = publishedOklch(oklch);
        expect(Math.abs(measured.L - L.value), `L ${measured.L}`).toBeLessThanOrEqual(L.unit);
        expect(Math.abs(measured.C - C.value), `C ${measured.C}`).toBeLessThanOrEqual(C.unit);
        expect(Math.abs(measured.h - h.value), `h ${measured.h}`).toBeLessThanOrEqual(h.unit);
    });

    it('gives a colour with no chroma the hue 0, and reads nothing it cannot: a colour that is not #rrggbb throws', () => {
        const black = oklchOf('#000000');
        expect({C: black.C, h: black.h}).toEqual({C: 0, h: 0});
        expect(oklchOf('#ffffff').C, 'white: a neutral, no chroma to speak of').toBeLessThan(1e-3);
        expect(oklchOf('#AAFF00'), 'barrier: the case of a hex does not matter').toEqual(oklchOf('#aaff00'));
        expect(() => oklchOf('green')).toThrow();
    });
});

// =============================================================================
// 8. §1.1, the rule of the greens
// =============================================================================

/** A colour a category is drawn in, and what draws it. */
interface Drawn {
    what: string;
    dark: boolean;
    colour: string;
}

/** Every colour a category is drawn in: each key of each table and each bucket, and each country of the sequence, in both themes. */
function everyCategoryColour(): Drawn[] {
    const keyed = KINDS.flatMap((kind) => [...CATEGORY_KEYS[kind], ...CATEGORY_BUCKETS].flatMap((key) => THEMES.map((dark) => ({what: `${kind} ${key}, ${themeName(dark)}`, dark, colour: same(categoryColor(kind, key, dark))}))));
    const countries = COUNTRY_SEQUENCE.flatMap((ref, index) => THEMES.map((dark) => ({what: `country ${index + 1} (${refName(ref)}), ${themeName(dark)}`, dark, colour: same(refColour(ref, dark))})));
    return [...keyed, ...countries];
}

/**
 * §1.1 in OKLCH, as the coordinator checked it (§0): green, teal, olive, lime and greenish cyan are the hues from 115° to
 * 225°. A grey is no green, whatever its hue: the band starts above a chroma of 0.03.
 */
const GREEN_BAND = {from: 115, to: 225, chroma: 0.03} as const;
/** How far from the success green a category stays (§0: «Nessun colore vicino al verde di successo»). */
const SUCCESS_APART = 10;
/** A category against its card, as any graphic object that carries meaning (WCAG 1.4.11). */
const CARD_CONTRAST = 3;

/** The colours in the green band, each with where it sits in it. */
function greens(drawn: readonly Drawn[]): string[] {
    return drawn.flatMap(({what, colour}) => {
        const {C, h} = oklchOf(colour);
        return C > GREEN_BAND.chroma && h >= GREEN_BAND.from && h <= GREEN_BAND.to ? [`${what} ${colour}: h ${h.toFixed(1)}°, C ${C.toFixed(3)}`] : [];
    });
}

/** The colours under ΔE00 10 from `success`, and those that are `danger`, whatever the case of either hex. */
function semanticOffenders(drawn: readonly Drawn[], success: string, danger: string): {nearSuccess: string[]; danger: string[]} {
    return {
        nearSuccess: drawn.filter(({colour}) => deltaE00(colour, success) < SUCCESS_APART).map(({what, colour}) => `${what} ${colour}: ΔE00 ${deltaE00(colour, success).toFixed(2)} from ${success}`),
        danger: drawn.filter(({colour}) => same(colour) === same(danger)).map(({what, colour}) => `${what} ${colour}`),
    };
}

/** The colours under 3:1 on `card`, by the colour gate's own WCAG formula. */
function faintOnCard(drawn: readonly Drawn[], card: string): string[] {
    return drawn.flatMap(({what, colour, dark}) => {
        const ratio = contrastRatio(resolveColour(TOKENS, colour, themeName(dark)), resolveColour(TOKENS, card, themeName(dark)));
        return ratio < CARD_CONTRAST ? [`${what} ${colour}: ${ratio.toFixed(2)}:1 on ${card}`] : [];
    });
}

/** Synthetic colours for the positive controls, named, in `dark`. */
const synthetic = (colours: Readonly<Record<string, string>>, dark: boolean): Drawn[] => Object.entries(colours).map(([what, colour]) => ({what, dark, colour}));

describe('§1.1, the rule of the greens — no category in a green, near the success green, in the danger red, or faint on its card', () => {
    it('barrier: the checks read every colour a category is drawn in — both tables, both buckets, the fourteen countries — in both themes', () => {
        const keyed = KINDS.reduce((sum, kind) => sum + CATEGORY_KEYS[kind].length + CATEGORY_BUCKETS.length, 0);
        expect(everyCategoryColour()).toHaveLength((keyed + COUNTRY_SEQUENCE.length) * THEMES.length);
    });

    it('takes no colour in the OKLCH green band, 115°–225° at a chroma over 0.03', () => {
        expect(greens(everyCategoryColour()), 'a category is a green, a teal, an olive, a lime or a greenish cyan (§1.1)').toEqual([]);
    });

    it('positive control: the check reads the colours live, through categoryColor — a cash edited back to the sage of round 2 is caught in both tables', () => {
        vi.stubGlobal('__LF_DESIGNER_LAB__', true);
        publishHook((_kind, key, dark) => (key === 'Liquidity' && !dark ? '#2D6A54' : null));

        expect(greens(everyCategoryColour()).map((line) => line.split(' #')[0])).toEqual(['type Liquidity, light', 'sector Liquidity, light']);
    });

    it('positive control: the band takes the greens round 3 removed, the success greens and a published lime; it leaves a published yellow and blue, and a grey of green hue', () => {
        const taken = {
            'the cash’s sage, round 2': '#2D6A54',
            'CROWDFUND’s teal, round 2': '#0D9488',
            'Consumer Staples’ olive, round 2': '#4D7C0F',
            'BOND’s petrol, round 2': '#0E7490',
            'hsl(80deg 100% 50%), CSS Color 4: oklch(0.91 0.245 129.9)': '#aaff00',
            'the light success green': tokenColour('--lf-success', false),
            'the dark success green': tokenColour('--lf-success', true),
        };
        expect(
            greens(synthetic(taken, false)).map((line) => line.split(' #')[0]),
            'greens the band lets through',
        ).toEqual(Object.keys(taken));

        const left = {
            'sRGB yellow, CSS Color 4: oklch(0.968 0.211 109.8)': '#ffff00',
            'sRGB blue, CSS Color 4: oklch(0.452 0.313 264.1)': '#0000ff',
            'OTHER’s stone grey, round 2: a green hue at a chroma under 0.02': '#6E7A74',
        };
        expect(greens(synthetic(left, false)), 'colours the band takes that are no green').toEqual([]);
    });

    it.each(THEME_CASES)('%s: every colour at least ΔE00 10 from the success green, and none the danger red — both read from tokens.css', (theme, dark) => {
        const drawn = everyCategoryColour().filter((entry) => entry.dark === dark);
        expect(drawn.length, 'barrier: the theme has its colours').toBeGreaterThan(0);

        const offenders = semanticOffenders(drawn, tokenColour('--lf-success', dark), tokenColour('--lf-danger', dark));
        expect(offenders.nearSuccess, `a category is near the ${theme} success green: its slice would read as a success, or a gain (§1.1)`).toEqual([]);
        expect(offenders.danger, `a category is the ${theme} danger red: its slice would read as an error, or a loss (§1.1)`).toEqual([]);
    });

    it('positive control: the checks take the success green itself and the round-2 sage of the cash, and the danger red written in another case', () => {
        const [success, danger] = [tokenColour('--lf-success', false), tokenColour('--lf-danger', false)];
        const drawn = synthetic({'the success green': success, 'the cash’s sage, round 2': '#2D6A54', 'the danger red, upper case': danger.toUpperCase(), ETF: designerValue('type', 'ETF', false)}, false);

        const offenders = semanticOffenders(drawn, success, danger);
        expect(offenders.nearSuccess.map((line) => line.split(' #')[0])).toEqual(['the success green', 'the cash’s sage, round 2']);
        expect(offenders.danger.map((line) => line.split(' #')[0])).toEqual(['the danger red, upper case']);
    });

    it.each(THEME_CASES)('%s: every colour at least 3:1 on the card, read from tokens.css (WCAG 1.4.11)', (theme, dark) => {
        const drawn = everyCategoryColour().filter((entry) => entry.dark === dark);
        expect(faintOnCard(drawn, tokenColour('--lf-surface-card', dark)), `a category is under 3:1 on the ${theme} card: its slice, its bar or its line fades into it`).toEqual([]);
    });

    it('positive control: the contrast check takes the card itself and the unclassified fog greys of round 2, each on its own card', () => {
        for (const dark of THEMES) {
            const card = tokenColour('--lf-surface-card', dark);
            const fog = dark ? '#52605B' : '#94A09B';
            const faint = faintOnCard(synthetic({'the card': card, 'the fog grey, round 2': fog, ETF: designerValue('type', 'ETF', dark)}, dark), card);
            expect(
                faint.map((line) => line.split(' #')[0]),
                themeName(dark),
            ).toEqual(['the card', 'the fog grey, round 2']);
        }
    });
});

// =============================================================================
// 9. Distinguishability (§1.8) — nothing under ΔE00 5; under 8, the pairs she kept
// =============================================================================

/** No two colours of one table are ever this close (§1.8: «Nessuna sotto 5»): no listing can let a pair under it. */
const HARD_FLOOR = 5;
/** Under this distance a pair is told apart by the legend and the tooltip alone: it must be one the designer kept. */
const NAMED_UNDER = 8;
/** How much closer than its record a named pair may measure: the record is rounded to two decimals. */
const TOLERANCE = 0.005;

interface ListedPair {
    pair: readonly [string, string];
    /** ΔE00 as this file's ruler measures it, rounded to two decimals. */
    measured: number;
}

/**
 * The pairs the designer kept between ΔE00 5 and 8 (§1.8), per table and theme, each with its measure — the fourteen of
 * §1.8, and `ETF · Liquidity`, the type table's twin of her `Technology · Liquidity` (ETF and Technology are one colour).
 * The buckets are in both tables; «Unknown» is beside the countries, which are named by their position in §1.4. The
 * measures are the ruler's of `$test/colorDistance`; the coordinator's (`dv_r3_pairs`, 17/10) agree within 0.01. Three
 * pairs sit just past 8 and are not named: `OTHER · Unknown` and `Other · Unknown` in light, and `country 14 ·
 * Unknown`, the same two greys, at 8.004. Shorten the list when a pair moves past 8; add none under 5.
 */
const CLOSE_PAIRS: Readonly<Record<string, readonly ListedPair[]>> = {
    'type light': [
        {pair: ['BOND', 'Liquidity'], measured: 5.31},
        {pair: ['ETF', 'Liquidity'], measured: 5.86},
        {pair: ['STOCK', 'FUND'], measured: 5.91},
        {pair: ['CROWDFUND', 'INDEX'], measured: 7.42},
    ],
    'type dark': [
        {pair: ['CROWDFUND', 'INDEX'], measured: 7.03},
        {pair: ['ETF', 'BOND'], measured: 7.35},
    ],
    'sector light': [
        {pair: ['Financials', 'Telecommunication'], measured: 5.21},
        {pair: ['Utilities', 'Liquidity'], measured: 5.33},
        {pair: ['Technology', 'Liquidity'], measured: 5.86},
        {pair: ['Industrials', 'Liquidity'], measured: 7.57},
        {pair: ['Industrials', 'Utilities'], measured: 7.91},
    ],
    'sector dark': [
        {pair: ['Technology', 'Utilities'], measured: 5.76},
        {pair: ['Financials', 'Consumer Discretionary'], measured: 7.26},
    ],
    'country light': [{pair: ['country 2', 'country 10'], measured: 5.91}],
    'country dark': [{pair: ['country 1', 'country 7'], measured: 5.76}],
};

interface Verdict {
    /** How many pairs were measured. */
    pairs: number;
    /** Pairs under the hard floor, named or not: no listing lets them through. */
    underFloor: string[];
    /** Pairs under 8 that the list does not name. */
    unlisted: string[];
    /** Named pairs now closer than their record, beyond the rounding. */
    closer: string[];
    /** Named pairs now at least 8 apart: the list should lose them. */
    apart: string[];
    /** Named pairs with a member the table does not have. */
    stale: string[];
}

const pairId = (first: string, second: string): string => [first, second].sort().join(' · ');

/** Every pair of `members` (`[key, colour]`), measured, and judged against the hard floor and against `listed`. */
function distinguishability(members: ReadonlyArray<readonly [string, string]>, listed: readonly ListedPair[]): Verdict {
    const records = new Map(listed.map((entry) => [pairId(...entry.pair), entry]));
    const verdict: Verdict = {pairs: 0, underFloor: [], unlisted: [], closer: [], apart: [], stale: []};
    const keys = new Set(members.map(([key]) => key));
    for (const {pair} of listed) if (!pair.every((key) => keys.has(key))) verdict.stale.push(pair.join(' · '));

    members.forEach(([firstKey, firstColour], i) => {
        members.slice(i + 1).forEach(([secondKey, secondColour]) => {
            verdict.pairs += 1;
            const distance = deltaE00(firstColour, secondColour);
            const record = records.get(pairId(firstKey, secondKey));
            const shown = `${firstKey} ${firstColour} · ${secondKey} ${secondColour}: ΔE00 ${distance.toFixed(2)}`;
            if (distance < HARD_FLOOR) {
                verdict.underFloor.push(record ? `${shown}, named at ${record.measured.toFixed(2)}` : shown);
            } else if (!record) {
                if (distance < NAMED_UNDER) verdict.unlisted.push(shown);
            } else if (distance >= NAMED_UNDER) {
                verdict.apart.push(shown);
            } else if (distance < record.measured - TOLERANCE) {
                verdict.closer.push(`${shown}, recorded ${record.measured.toFixed(2)}`);
            }
        });
    });
    return verdict;
}

/** The members of one table in one theme, as a chart draws them side by side. */
type Members = ReadonlyArray<readonly [string, string]>;

/** The six tables of the gate, each read when its case runs: each kind with both buckets, and the fourteen countries with «Unknown», in each theme. */
const TABLE_THEMES: ReadonlyArray<readonly [string, () => Members]> = [
    ...KINDS.flatMap((kind) => THEMES.map((dark) => [`${kind} ${themeName(dark)}`, (): Members => [...CATEGORY_KEYS[kind], ...CATEGORY_BUCKETS].map((key) => [key, categoryColor(kind, key, dark)] as const)] as const)),
    ...THEMES.map((dark) => [`country ${themeName(dark)}`, (): Members => [...COUNTRY_SEQUENCE.map((ref, index) => [`country ${index + 1}`, refColour(ref, dark)] as const), ['Unknown', categoryColor('sector', 'Unknown', dark)] as const]] as const),
];

describe('distinguishability (§1.8) — no pair of a table under ΔE00 5; under 8, only the pairs the designer kept', () => {
    it.each(TABLE_THEMES)('%s', (name, membersOf) => {
        const members = membersOf();
        const verdict = distinguishability(members, CLOSE_PAIRS[name] ?? []);

        expect(verdict.pairs, 'barrier: every pair of the table was measured').toBe((members.length * (members.length - 1)) / 2);
        expect(verdict.stale, `the list for ${name} names a key the table does not have: fix the list`).toEqual([]);
        expect(verdict.underFloor, `these pairs of ${name} are under ΔE00 ${HARD_FLOOR}: §1.8 allows none, named or not — a slice next to the other is the same colour`).toEqual([]);
        expect(verdict.unlisted, `these pairs of ${name} are under ΔE00 ${NAMED_UNDER} and not among the ones the designer kept (§1.8): a slice next to the other would be confused with it`).toEqual([]);
        expect(verdict.closer, `these named pairs of ${name} are now closer than recorded: the values moved, toward each other`).toEqual([]);
        expect(verdict.apart, `these named pairs of ${name} are now at least ΔE00 ${NAMED_UNDER} apart: shorten CLOSE_PAIRS`).toEqual([]);
    });

    it('names exactly fifteen pairs, in the six tables: the fourteen of §1.8, and ETF · Liquidity, the type table’s twin of Technology · Liquidity', () => {
        expect(Object.values(CLOSE_PAIRS).flat()).toHaveLength(15);
        expect(Object.keys(CLOSE_PAIRS).sort()).toEqual(TABLE_THEMES.map(([name]) => name).sort());
        expect(colourPair('type', 'ETF'), 'premise of the twin: ETF and Technology are one colour, in both themes').toBe(colourPair('sector', 'Technology'));
        expect(
            Object.values(CLOSE_PAIRS)
                .flat()
                .filter(({measured}) => measured < HARD_FLOOR || measured >= NAMED_UNDER)
                .map(({pair}) => pair.join(' · ')),
            'a record outside [5, 8): under 5 no pair may be named, from 8 none needs to be',
        ).toEqual([]);
    });

    it('the gate fails on what it guards against: a pair under 5 even when named, an unnamed pair under 8, a named pair closer than recorded, one now apart, one stale', () => {
        const [A, B, C, D, E] = ['#777777', '#8a8a8a', '#a0a0a0', '#7a7a7a', '#0000ff'];
        // Premises: the synthetic greys sit where the cases need them.
        expect(deltaE00(A, D), 'A · D, under the hard floor').toBeLessThan(HARD_FLOOR);
        for (const [first, second] of [
            [A, B],
            [B, C],
            [B, D],
        ]) {
            expect(deltaE00(first, second), `${first} · ${second}, between 5 and 8`).toBeGreaterThanOrEqual(HARD_FLOOR);
            expect(deltaE00(first, second), `${first} · ${second}, between 5 and 8`).toBeLessThan(NAMED_UNDER);
        }
        expect(deltaE00(A, B), 'A · B, closer than the record it is given').toBeLessThan(7.5 - TOLERANCE);
        expect(deltaE00(B, D), 'B · D, at the record it is given').toBeGreaterThanOrEqual(5.9);

        const members = [
            ['A', A],
            ['B', B],
            ['C', C],
            ['D', D],
            ['E', E],
        ] as const;
        const verdict = distinguishability(members, [
            {pair: ['A', 'D'], measured: 1.2},
            {pair: ['A', 'B'], measured: 7.5},
            {pair: ['A', 'C'], measured: 7.9},
            {pair: ['B', 'D'], measured: 5.9},
            {pair: ['A', 'Z'], measured: 6.0},
        ]);

        expect(verdict.pairs).toBe(10);
        expect(
            verdict.underFloor.map((line) => line.split(':')[0]),
            'named or not, under 5 is red',
        ).toEqual([`A ${A} · D ${D}`]);
        expect(verdict.unlisted.map((line) => line.split(':')[0])).toEqual([`B ${B} · C ${C}`]);
        expect(verdict.closer.map((line) => line.split(':')[0])).toEqual([`A ${A} · B ${B}`]);
        expect(verdict.apart.map((line) => line.split(':')[0])).toEqual([`A ${A} · C ${C}`]);
        expect(verdict.stale).toEqual(['A · Z']);
    });

    it('the gate passes a table whose only pair under 8 is named, at its record or past it', () => {
        const verdict = distinguishability(
            [
                ['A', '#777777'],
                ['B', '#8a8a8a'],
                ['E', '#0000ff'],
            ],
            [{pair: ['B', 'A'], measured: 7.1}],
        );

        expect(verdict).toEqual({pairs: 3, underFloor: [], unlisted: [], closer: [], apart: [], stale: []});
    });
});

// =============================================================================
// 10. Parity with T's category roles (§1.9, decision A)
// =============================================================================

/**
 * Whether T's category roles are in tokens.css — T's batch, `lib/theme/tokens.css`, round 3: the badges of §1.9 are HTML
 * and read classes, so the type colours become roles there (decision A). While false, none of them may be declared; the
 * batch that lands second — T's roles after this test, or this test after T's roles — flips it to true, and from then on
 * each role is held to `categoryColor` of its key, in both themes. Their `-soft` and `-on-soft` derivatives, the
 * badge's tint and its text, are T's contrast gate (`src/themeTokens.gate.test.ts`), not this test.
 *
 * True since 18/10/2026: T's roles landed first (R3-b, `7845fc3d3`), and DV flipped the flag at its merge of the target.
 * Since DV-11 (22/10/2026) a type colour lives in one place, its role: `categoryColor` reads it (the stand-ins of
 * `roleColors.ts` here, where no page is loaded), so this block now checks that the read and tokens.css agree.
 */
const CATEGORY_ROLES_IN_TOKENS = true;

/** The base role of each type of the table and of the cash: the type key lower-cased, `_` → `-`; `Liquidity`, the bucket. */
const TOKEN_CATEGORY_ROLES: ReadonlyArray<readonly [role: string, key: string]> = [
    ['--lf-cat-stock', 'STOCK'],
    ['--lf-cat-etf', 'ETF'],
    ['--lf-cat-bond', 'BOND'],
    ['--lf-cat-crypto', 'CRYPTO'],
    ['--lf-cat-fund', 'FUND'],
    ['--lf-cat-hold', 'HOLD'],
    ['--lf-cat-crowdfund', 'CROWDFUND'],
    ['--lf-cat-commodity', 'COMMODITY'],
    ['--lf-cat-real-estate', 'REAL_ESTATE'],
    ['--lf-cat-index', 'INDEX'],
    ['--lf-cat-other', 'OTHER'],
    ['--lf-cat-liquidity', 'Liquidity'],
];

type Tokens = ReturnType<typeof readTokens>;

/** The category roles a token set declares, theme by theme. */
function declaredCategoryRoles(tokens: Tokens): string[] {
    return TOKEN_CATEGORY_ROLES.flatMap(([role]) => THEMES.filter((dark) => tokenValue(tokens, role, themeName(dark)) !== undefined).map((dark) => `${role} (${themeName(dark)})`));
}

/**
 * Why the category roles of a token set are not the charts' colours — empty when each is declared in both themes, is
 * opaque, and resolves to `categoryColor('type', key)` of its theme, whatever the case of either hex.
 */
function categoryRoleMismatches(tokens: Tokens): string[] {
    return TOKEN_CATEGORY_ROLES.flatMap(([role, key]) =>
        THEMES.flatMap((dark) => {
            const theme = themeName(dark);
            if (tokenValue(tokens, role, theme) === undefined) return [`${role} (${theme}): not declared`];
            const resolved = resolveColour(tokens, `var(${role})`, theme);
            if (resolved.alpha < 1) return [`${role} (${theme}): translucent, alpha ${resolved.alpha} — a category role is opaque`];
            const [hex, expected] = [toHex(resolved).toLowerCase(), categoryColor('type', key, dark).toLowerCase()];
            return hex === expected ? [] : [`${role} (${theme}): resolves ${hex}, categoryColor('type', '${key}') is ${expected}`];
        }),
    );
}

/** A token set of the two theme blocks, as tokens.css writes them: what the comparison is proven on. */
function tokenSet(light: Readonly<Record<string, string>>, dark: Readonly<Record<string, string>>): Tokens {
    const block = (selector: string, roles: Readonly<Record<string, string>>) => {
        const declarations = Object.entries(roles).map(([role, value]) => `    ${role}: ${value};`);
        return `${selector} {\n${declarations.join('\n')}\n}`;
    };
    return parseTokens(`${block(TOKEN_BLOCKS.light, light)}\n${block(TOKEN_BLOCKS.dark, dark)}`);
}

/** The twelve roles at the charts' colours of a theme, as `categoryColor` writes them. */
const chartRoleValues = (dark: boolean): Record<string, string> => Object.fromEntries(TOKEN_CATEGORY_ROLES.map(([role, key]) => [role, categoryColor('type', key, dark)]));

describe("parity with T's category roles (§1.9, decision A) — one colour per type, in tokens.css and in the charts", () => {
    it('names one role per type of the table and one for the cash, by the rule: the key lower-cased, `_` → `-`', () => {
        expect(TOKEN_CATEGORY_ROLES.map(([, key]) => key)).toEqual([...CATEGORY_KEYS.type, 'Liquidity']);
        expect(TOKEN_CATEGORY_ROLES.filter(([role, key]) => role !== `--lf-cat-${key.toLowerCase().replace(/_/g, '-')}`).map(([role]) => role)).toEqual([]);
    });

    it(CATEGORY_ROLES_IN_TOKENS ? 'tokens.css declares each role in both themes, at the colour categoryColor gives its key' : 'tokens.css declares no category role yet: T’s batch has not landed', () => {
        if (CATEGORY_ROLES_IN_TOKENS) {
            expect(categoryRoleMismatches(TOKENS), 'CATEGORY_ROLES_IN_TOKENS is true: every --lf-cat-* role must be in tokens.css, in both themes, at the charts’ colour of its key').toEqual([]);
        } else {
            expect(declaredCategoryRoles(TOKENS), 'tokens.css declares category roles: T’s batch has landed. Whoever lands second flips CATEGORY_ROLES_IN_TOKENS to true in chartCategories.test.ts, and the roles are held to categoryColor').toEqual([]);
        }
    });

    it('positive control: the comparison passes a token set at the charts’ colours — in any case, through a var() — and names a role missing, a translucent one and a wrong colour', () => {
        const light = chartRoleValues(false);
        // Dark: lower case, and the cash through a var() of its own, as a role may be written.
        const dark = {...Object.fromEntries(Object.entries(chartRoleValues(true)).map(([role, value]) => [role, value.toLowerCase()])), '--lf-slate': chartRoleValues(true)['--lf-cat-liquidity'], '--lf-cat-liquidity': 'var(--lf-slate)'};
        const matching = tokenSet(light, dark);
        expect(declaredCategoryRoles(matching), 'barrier: the set declares the twelve roles in both themes').toHaveLength(TOKEN_CATEGORY_ROLES.length * THEMES.length);
        expect(categoryRoleMismatches(matching)).toEqual([]);

        const without = (roles: Readonly<Record<string, string>>, ...gone: string[]) => Object.fromEntries(Object.entries(roles).filter(([role]) => !gone.includes(role)));
        const wrong = tokenSet({...without(light, '--lf-cat-index'), '--lf-cat-stock': `color-mix(in oklab, ${light['--lf-cat-stock']} 50%, transparent)`, '--lf-cat-etf': '#123456'}, without(dark, '--lf-cat-bond', '--lf-cat-index'));
        expect(categoryRoleMismatches(wrong)).toEqual([
            '--lf-cat-stock (light): translucent, alpha 0.5 — a category role is opaque',
            `--lf-cat-etf (light): resolves #123456, categoryColor('type', 'ETF') is ${light['--lf-cat-etf'].toLowerCase()}`,
            '--lf-cat-bond (dark): not declared',
            '--lf-cat-index (light): not declared',
            '--lf-cat-index (dark): not declared',
        ]);
        expect(declaredCategoryRoles(tokenSet({'--lf-text-primary': '#1c2420'}, {'--lf-text-primary': '#e8ece9'})), 'a token set with no category role declares none').toEqual([]);
    });
});
