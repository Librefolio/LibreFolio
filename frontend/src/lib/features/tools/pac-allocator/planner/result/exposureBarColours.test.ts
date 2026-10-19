// @vitest-environment node
/**
 * exposureBarColours — the colours of the PAC's exposure bars, «ideal vs actual» (TD-1, R9.8; the coordinator,
 * 15/10/2026; the designer's round 3, §1.7).
 *
 * - **The actual weight** takes its row's category colour, the dashboard's (GR1), in the order of the rows:
 *   - a sector its colour by key;
 *   - an Asset type its family's colour, and a subtype a shade of it, ranked as in the pie's outer ring (GR4): the
 *     generic member keeps the family's colour; the subtypes take `familyShade` by rank among their own family's
 *     subtypes, largest ideal weight first (`compareExact`, exact across a decimal and a ratio), ties by id. A subtype
 *     never takes the family's own colour, even with no generic member beside it;
 *   - the uncategorised remainder, in either dimension, the unclassified bucket (`Unknown`); a type outside the table
 *     (`warrant`) the unclassified colour too.
 * - **The ideal weight** wears the designer's neutral grey, a value of its own and no role: `idealColour(dark)` is
 *   `PAC_EXPOSURE_COLORS.ideal` of the theme, light `#8C929E` and dark `#868594` — her choice of 17/10/2026 (P1-a′,
 *   P2-c), after `decisioni.md` §1.7 and `palette-finale.json`, which still show the grey she replaced.
 * - **The rule of the 10s** (TD-1, the coordinator's decision). The ideal stays at least ΔE00 10 from every colour a row
 *   can draw — each key of both tables, both buckets, and every subtype shade (`familyShade`, from rank 1 to the size
 *   of the family: the six of ETF, the one of CROWDFUND) on the poles of the card the bars sit on,
 *   `--lf-surface-card` as tokens.css resolves it — so a row's colour belongs to its actual weight alone. Exactly two
 *   recorded exceptions, both in the light theme: «Unknown», the unclassified bucket, and the «Other» grey that
 *   `OTHER` and `Other` share (§1.7). The dark theme has none. The guard fails if an exception drops below its record,
 *   if any other colour goes under 10, and if an exception is no longer needed, so it does not outlive its reason. The
 *   ideal is also at least 3:1 on the card in both themes (WCAG 1.4.11). The ruler is `$test/colorDistance`, checked on
 *   published data first; every red path is shown on synthetic colours.
 *
 * Every expected colour is computed from the public functions (`categoryColor`, `familyShade`, `PAC_EXPOSURE_COLORS`),
 * never copied: the values are the designer's, the rule is this module's. Her two greys are written out once, where
 * their choice is pinned. Exact weights are written as `model.test.ts` writes them.
 *
 * Node env. The module imports `assetTypeFamily` (the generated API schemas) and the planner's model, whose formatter
 * imports the API client: the client is mocked inert, as in `model.test.ts`.
 *
 * @module features/tools/pac-allocator/planner/result/exposureBarColours.test
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

// The model imports the planner's formatter, which reads the currency catalogue store, which imports the API client.
// Nothing here formats an amount: every call resolves to nothing.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
}));

import {contrastRatio, readTokens, resolveColour, toHex} from '../../../../../../../scripts/theme/theme-roles.mjs';
import {ciede2000, deltaE00, SHARMA_PAIRS} from '$test/colorDistance';
import {CATEGORY_BUCKETS, CATEGORY_KEYS, categoryColor, type CategoryKind} from '$lib/theme/chartCategories';
import {familyShade, shadePoles, type ShadePoles} from '$lib/theme/chartShades';
import {PAC_EXPOSURE_COLORS} from '$lib/theme/chartTheme';
import {setRoleReader} from '$lib/theme/roleColors';
import {themed} from '$lib/theme/themePair';
import {ASSET_TYPE_FAMILY} from '$lib/utils/assetTypes';
import type {PacExactNumber} from '../types';
import {actualColours, idealColour} from './exposureBarColours';
import {compareExact, UNCATEGORISED_CATEGORY_ID, type WeightRow} from './model';

afterEach(() => {
    setRoleReader(null);
});

// =============================================================================
// Rows, as the bars receive them
// =============================================================================

/** An ideal weight as the backend publishes a finite decimal. */
const decimal = (value: string): PacExactNumber => ({kind: 'finite_decimal', value});

/** An ideal weight as an exact ratio; its display fields are never read here. */
const ratio = (numerator: string, denominator: string, display: string): PacExactNumber => ({kind: 'exact_ratio', numerator, denominator, display_decimal: display, display_scale: 6, display_authority: 'non_authoritative'});

/** A row of the bars: its category id and its ideal weight. The label and the final weight play no part in the colour. */
function row(id: string, target: PacExactNumber): WeightRow {
    return {id, label: id, target, final: {kind: 'available', value: target}};
}

const THEMES = [
    ['light', false],
    ['dark', true],
] as const;

/** The dark card of the designer's round 2. Any card would do: the expectations use the same poles as the call. */
const CARD = '#151B19';
const poles = (dark: boolean): ShadePoles => shadePoles(dark, CARD);

/** A family's colour in the types' table. */
const typeColour = (family: string, dark: boolean): string => categoryColor('type', family, dark);

/** The shade of rank `rank` of a family, as the pie's outer ring draws it. */
const shadeOf = (family: string, rank: number, dark: boolean): string => familyShade(typeColour(family, dark), rank, poles(dark));

// =============================================================================
// The actual weight
// =============================================================================

describe('actualColours — the premises its expectations rest on', () => {
    it.each(THEMES)('%s: the base and its first three shades are four colours, for each family the cases use, and none is the unclassified colour', (_theme, dark) => {
        const unclassified = categoryColor('type', 'Unknown', dark);
        for (const family of ['ETF', 'CROWDFUND']) {
            const members = [0, 1, 2, 3].map((rank) => shadeOf(family, rank, dark));
            expect(new Set(members).size, `${family}: a rank mixed up would go unseen`).toBe(4);
            expect(members, family).not.toContain(unclassified);
        }
    });
});

describe('actualColours — a sector reads its own colour, in the order of the rows', () => {
    it.each(THEMES)('%s: each sector its colour by key', (_theme, dark) => {
        const rows = [row('Technology', decimal('0.4')), row('Health Care', decimal('0.3')), row('Other', decimal('0.2')), row('Energy', decimal('0.1'))];
        const expected = ['Technology', 'Health Care', 'Other', 'Energy'].map((key) => categoryColor('sector', key, dark));
        expect(new Set(expected).size, 'barrier: four distinct colours, so the order is seen').toBe(4);

        expect(actualColours(rows, 'sector', dark, poles(dark))).toEqual(expected);
    });
});

describe('actualColours — an Asset type reads its family, a subtype a shade of it (GR4)', () => {
    it.each(THEMES)('%s: the generic member keeps the family colour; its subtypes take shades 1 and 2, the larger ideal weight first, whatever the order of the rows', (_theme, dark) => {
        const rows = [row('ETF_BOND', decimal('0.1')), row('ETF', decimal('0.2')), row('ETF_STOCK', decimal('0.35'))];

        expect(actualColours(rows, 'asset_type', dark, poles(dark))).toEqual([shadeOf('ETF', 2, dark), typeColour('ETF', dark), shadeOf('ETF', 1, dark)]);
    });

    it.each(THEMES)('%s: two subtypes of one ideal weight are ranked by id, the weight compared exactly across a ratio and a decimal', (_theme, dark) => {
        const quarter = ratio('1', '4', '0.25');
        expect(compareExact(quarter, decimal('0.25')), 'premise: 1/4 and 0.25 are one weight').toBe(0);
        const rows = [row('ETF', decimal('0.5')), row('ETF_STOCK', quarter), row('ETF_BOND', decimal('0.25'))];

        expect(actualColours(rows, 'asset_type', dark, poles(dark)), 'ETF_BOND before ETF_STOCK, by id, though listed after it').toEqual([typeColour('ETF', dark), shadeOf('ETF', 2, dark), shadeOf('ETF', 1, dark)]);
    });

    it.each(THEMES)('%s: a family with no generic member: its subtypes still take shades, never the family colour', (_theme, dark) => {
        const etf = actualColours([row('ETF_STOCK', decimal('0.6')), row('ETF_BOND', decimal('0.4'))], 'asset_type', dark, poles(dark));
        expect(etf).toEqual([shadeOf('ETF', 1, dark), shadeOf('ETF', 2, dark)]);
        expect(etf, 'no subtype takes the family colour').not.toContain(typeColour('ETF', dark));

        expect(actualColours([row('CROWDFUND_REAL_ESTATE', decimal('1'))], 'asset_type', dark, poles(dark)), 'a lone subtype: shade 1').toEqual([shadeOf('CROWDFUND', 1, dark)]);
    });

    it.each(THEMES)('%s: two families are ranked each on its own: the subtypes of each start at shade 1', (_theme, dark) => {
        // CROWDFUND_REAL_ESTATE has the smallest ideal weight of all: ranked across families it would be third.
        const rows = [row('ETF_STOCK', decimal('0.3')), row('CROWDFUND_REAL_ESTATE', decimal('0.05')), row('ETF_BOND', decimal('0.2')), row('CROWDFUND', decimal('0.1')), row('STOCK', decimal('0.35'))];

        expect(actualColours(rows, 'asset_type', dark, poles(dark))).toEqual([shadeOf('ETF', 1, dark), shadeOf('CROWDFUND', 1, dark), shadeOf('ETF', 2, dark), typeColour('CROWDFUND', dark), typeColour('STOCK', dark)]);
    });
});

describe('actualColours — what reads as unclassified', () => {
    it.each(THEMES)('%s: the uncategorised remainder reads the unclassified bucket, in both dimensions', (_theme, dark) => {
        const table: Record<string, CategoryKind> = {asset_type: 'type', sector: 'sector'};
        for (const [dimension, kind] of Object.entries(table)) {
            const rows = [row(kind === 'type' ? 'STOCK' : 'Technology', decimal('0.7')), row(UNCATEGORISED_CATEGORY_ID, decimal('0.3'))];
            expect(actualColours(rows, dimension, dark, poles(dark)), dimension).toEqual([categoryColor(kind, rows[0].id, dark), categoryColor(kind, 'Unknown', dark)]);
        }
    });

    it.each(THEMES)('%s: a type outside the table, as written (warrant), reads the unclassified colour', (_theme, dark) => {
        const rows = [row('STOCK', decimal('0.8')), row('warrant', decimal('0.2'))];

        expect(actualColours(rows, 'asset_type', dark, poles(dark))).toEqual([typeColour('STOCK', dark), categoryColor('type', 'Unknown', dark)]);
    });
});

// =============================================================================
// The ideal weight
// =============================================================================

describe('idealColour — the designer’s neutral grey, a value of its own (§1.7)', () => {
    it.each(THEMES)('%s: PAC_EXPOSURE_COLORS.ideal of the theme', (_theme, dark) => {
        expect(idealColour(dark)).toBe(themed(PAC_EXPOSURE_COLORS.ideal, dark));
    });

    it('is the grey she chose on 17/10/2026: light #8C929E (P1-a′), dark #868594 (P2-c) — not the one §1.7 still shows', () => {
        // Her values, pinned here once: decisioni.md §1.7 and palette-finale.json still write #8B929E and #858E9B.
        expect(PAC_EXPOSURE_COLORS.ideal).toEqual({light: '#8C929E', dark: '#868594'});
    });

    it('reads no role: a page whose secondary text is another colour leaves it where it is', () => {
        // Until round 3 the ideal was the secondary text role (TD-1): a reader answering every role proves it is no more.
        const before = [idealColour(false), idealColour(true)];
        setRoleReader(() => '#123456');

        expect([idealColour(false), idealColour(true)]).toEqual(before);
    });
});

// =============================================================================
// The rule of the 10s — the ideal apart from every colour a row can draw
// =============================================================================

type Theme = (typeof THEMES)[number][0];

/** Under this distance two colours side by side are confused (`analisi.md` §4): the coordinator's floor for TD-1. */
const FLOOR = 10;
/** How much closer than its record an exception may measure: the record is rounded to two decimals. */
const TOLERANCE = 0.005;
/** The ideal against the card it is drawn on, as any graphic object that carries meaning (WCAG 1.4.11). */
const CARD_CONTRAST = 3;

/** Colours allowed under the floor, in one theme, at no less than their recorded distance. */
interface Exception {
    theme: Theme;
    /** The categories carrying the excepted colour, as `rowColours` names them. */
    categories: readonly string[];
    /** ΔE00 from the ideal, as this file's ruler measures it, rounded to two decimals. */
    recorded: number;
}

/**
 * The two recorded exceptions, both in the light theme, accepted with the grey (§1.7): «Unknown», the unclassified
 * bucket, measured 8.046; and the «Other» grey that OTHER and Other share, measured 8.696 (8.69 in the coordinator's
 * measure). The dark theme has none: its nearest colour, «Unknown» again, is at 10.07.
 */
const EXCEPTIONS: readonly Exception[] = [
    {theme: 'light', categories: ['bucket Unknown'], recorded: 8.05},
    {theme: 'light', categories: ['type OTHER', 'sector Other'], recorded: 8.7},
];

/** tokens.css, parsed by the colour gate's own module. */
const TOKENS = readTokens();

/** The card the bars sit on, `--lf-surface-card` as tokens.css resolves it: the near pole of the dark shades. */
const cardOf = (dark: boolean): string => toHex(resolveColour(TOKENS, 'var(--lf-surface-card)', dark ? 'dark' : 'light'));

/** How many subtypes each family has (`ASSET_TYPE_FAMILY`): a row of the family can take the shades 1 to that count. */
function subtypeCounts(): Map<string, number> {
    const counts = new Map<string, number>();
    for (const family of Object.values(ASSET_TYPE_FAMILY)) counts.set(family, (counts.get(family) ?? 0) + 1);
    return counts;
}

/**
 * Every colour a row of the bars can draw in a theme: each key of both tables, the two buckets both tables share, and
 * every subtype shade of every family, on the poles of the card from tokens.css.
 */
function rowColours(dark: boolean): Array<{category: string; colour: string}> {
    const kinds: readonly CategoryKind[] = ['type', 'sector'];
    const keyed = kinds.flatMap((kind) => CATEGORY_KEYS[kind].map((key) => ({category: `${kind} ${key}`, colour: categoryColor(kind, key, dark)})));
    const buckets = CATEGORY_BUCKETS.map((key) => ({category: `bucket ${key}`, colour: categoryColor('type', key, dark)}));
    const cardPoles = shadePoles(dark, cardOf(dark));
    const shades = [...subtypeCounts()].flatMap(([family, count]) => Array.from({length: count}, (_, index) => ({category: `${family} shade ${index + 1}`, colour: familyShade(categoryColor('type', family, dark), index + 1, cardPoles)})));
    return [...keyed, ...buckets, ...shades];
}

interface GuardVerdict {
    /** How many colours were measured. */
    measured: number;
    /** Colours under the floor that no exception covers. */
    under: string[];
    /** Excepted colours now closer than recorded. */
    closer: string[];
    /** Excepted colours now at the floor or past it: the exception has outlived its reason. */
    unneeded: string[];
    /** Excepted categories the measure never met. */
    stale: string[];
}

/** The ideal of `theme` measured against every colour, and judged against the floor and the exceptions of its theme. */
function guard(ideal: string, theme: Theme, colours: ReadonlyArray<{category: string; colour: string}>, exceptions: readonly Exception[]): GuardVerdict {
    const own = exceptions.filter((exception) => exception.theme === theme);
    const exceptionOf = (category: string) => own.find((exception) => exception.categories.includes(category));
    const verdict: GuardVerdict = {measured: 0, under: [], closer: [], unneeded: [], stale: own.flatMap(({categories}) => categories.filter((category) => !colours.some((entry) => entry.category === category)))};
    for (const {category, colour} of colours) {
        verdict.measured += 1;
        const distance = deltaE00(ideal, colour);
        const shown = `${theme} ${category} ${colour}: ΔE00 ${distance.toFixed(2)} from the ideal ${ideal}`;
        const exception = exceptionOf(category);
        if (!exception) {
            if (distance < FLOOR) verdict.under.push(shown);
        } else if (distance >= FLOOR) {
            verdict.unneeded.push(shown);
        } else if (distance < exception.recorded - TOLERANCE) {
            verdict.closer.push(`${shown}, recorded ${exception.recorded.toFixed(2)}`);
        }
    }
    return verdict;
}

/** The pair a verdict line names, without its measure. */
const pairOf = (line: string): string => line.split(':')[0];

describe('the rule of the 10s — the ideal stays apart from every colour a row can draw (TD-1, §1.7)', () => {
    it.each(THEMES)('%s: at least ΔE00 10 from every type, sector, bucket and subtype shade, but the recorded exceptions of the theme', (theme, dark) => {
        const verdict = guard(idealColour(dark), theme, rowColours(dark), EXCEPTIONS);

        expect(subtypeCounts().get('ETF'), 'barrier: the six shades of the ETF subtypes are among the colours').toBe(6);
        expect(verdict.measured, 'barrier: every key of both tables, both buckets and every subtype shade was measured').toBe(CATEGORY_KEYS.type.length + CATEGORY_KEYS.sector.length + CATEGORY_BUCKETS.length + Object.keys(ASSET_TYPE_FAMILY).length);
        expect(verdict.stale, 'an exception names a category the colours no longer have: record it again').toEqual([]);
        expect(verdict.under, `these colours are closer than ΔE00 ${FLOOR} to the ideal weight: its bar would read as that category`).toEqual([]);
        expect(verdict.closer, 'an excepted colour is closer to the ideal than recorded: the values moved toward each other').toEqual([]);
        expect(verdict.unneeded, `an excepted colour is now at least ΔE00 ${FLOOR} from the ideal: remove its exception`).toEqual([]);
    });

    it('records exactly two exceptions, both in the light theme: «Unknown» and the «Other» grey, each one colour', () => {
        expect(EXCEPTIONS.map(({theme, categories}) => `${theme}: ${categories.join(' + ')}`)).toEqual(['light: bucket Unknown', 'light: type OTHER + sector Other']);
        const colours = rowColours(false);
        for (const {categories} of EXCEPTIONS) {
            const excepted = colours.filter(({category}) => categories.includes(category));
            expect(
                excepted.map(({category}) => category),
                'barrier: the excepted categories are among the colours',
            ).toEqual([...categories]);
            expect(new Set(excepted.map(({colour}) => colour.toUpperCase())).size, `${categories.join(' and ')}: one colour`).toBe(1);
        }
    });

    it('positive control: the ruler reproduces the published CIEDE2000 data, and the closest colours are where the records put them', () => {
        const misses = SHARMA_PAIRS.filter(({first, second, deltaE}) => Math.abs(ciede2000(first, second) - deltaE) > 1e-4).map(({pair}) => pair);
        expect(misses, 'pairs of Sharma, Wu & Dalal (2005) the ruler does not reproduce').toEqual([]);

        const closest = (dark: boolean) =>
            rowColours(dark)
                .map(({category, colour}) => ({category, distance: deltaE00(idealColour(dark), colour)}))
                .sort((a, b) => a.distance - b.distance);
        // Light: the three closest colours are the excepted ones, each between its record and the floor.
        const light = closest(false).slice(0, 3);
        expect(light.map(({category}) => category).sort()).toEqual(EXCEPTIONS.flatMap(({categories}) => categories).sort());
        for (const {category, distance} of light) {
            expect(distance, category).toBeGreaterThanOrEqual(EXCEPTIONS.find(({categories}) => categories.includes(category))!.recorded - TOLERANCE);
            expect(distance, category).toBeLessThan(FLOOR);
        }
        // Dark: the closest colour is the floor or past it — «Unknown», by a tenth.
        const [nearestDark] = closest(true);
        expect(nearestDark.category).toBe('bucket Unknown');
        expect(nearestDark.distance).toBeGreaterThanOrEqual(FLOOR);
    });

    it.each(THEMES)('%s: at least 3:1 on the card it is drawn on (WCAG 1.4.11)', (theme, dark) => {
        const card = cardOf(dark);
        const ratio = contrastRatio(resolveColour(TOKENS, idealColour(dark), theme), resolveColour(TOKENS, card, theme));

        expect(ratio, `the ${theme} ideal ${idealColour(dark)} on the card ${card}`).toBeGreaterThanOrEqual(CARD_CONTRAST);
    });

    it('positive control: the contrast check takes the grey the ideal replaced in light, #9CA3AF at 2.45:1 (§1.7)', () => {
        const ratio = contrastRatio(resolveColour(TOKENS, '#9CA3AF', 'light'), resolveColour(TOKENS, cardOf(false), 'light'));

        expect(ratio).toBeLessThan(CARD_CONTRAST);
    });
});

describe('the rule of the 10s — each red path, on synthetic colours', () => {
    /** A synthetic ideal and its neighbours, at the distances the cases need (checked below). */
    const IDEAL = '#808080';
    const NEAR = '#868686';
    const FAR = '#ff0000';
    const TOO_CLOSE = '#959595';
    const BETWEEN = '#9c9c9c';
    const APART = '#a0a0a0';
    /** A record of the synthetic cases: TOO_CLOSE under it, BETWEEN past it and under the floor. */
    const RECORD = 9.0;

    it('premise: the synthetic colours sit where the cases need them', () => {
        expect(deltaE00(IDEAL, NEAR), 'under the floor').toBeLessThan(FLOOR);
        expect(deltaE00(IDEAL, FAR), 'past the floor').toBeGreaterThanOrEqual(FLOOR);
        expect(deltaE00(IDEAL, TOO_CLOSE), 'under the record').toBeLessThan(RECORD - TOLERANCE);
        expect(deltaE00(IDEAL, BETWEEN), 'between the record and the floor').toBeGreaterThanOrEqual(RECORD);
        expect(deltaE00(IDEAL, BETWEEN), 'between the record and the floor').toBeLessThan(FLOOR);
        expect(deltaE00(IDEAL, APART), 'past the floor').toBeGreaterThanOrEqual(FLOOR);
    });

    it('passes a clean measure: every colour past the floor, the excepted one between its record and the floor', () => {
        const colours = [
            {category: 'clean', colour: FAR},
            {category: 'excepted', colour: BETWEEN},
        ];
        const verdict = guard(IDEAL, 'light', colours, [{theme: 'light', categories: ['excepted'], recorded: RECORD}]);

        expect(verdict).toEqual({measured: 2, under: [], closer: [], unneeded: [], stale: []});
    });

    it('names a colour under the floor it does not cover, an excepted one closer than recorded, one no longer needed, and one it never met — across several exceptions', () => {
        const colours = [
            {category: 'near', colour: NEAR},
            {category: 'clean', colour: FAR},
            {category: 'excepted close', colour: TOO_CLOSE},
            {category: 'excepted apart', colour: APART},
        ];
        const verdict = guard(IDEAL, 'light', colours, [
            {theme: 'light', categories: ['excepted close', 'gone'], recorded: RECORD},
            {theme: 'light', categories: ['excepted apart'], recorded: RECORD},
        ]);

        expect(verdict.measured).toBe(4);
        expect(verdict.under.map(pairOf)).toEqual([`light near ${NEAR}`]);
        expect(verdict.closer.map(pairOf)).toEqual([`light excepted close ${TOO_CLOSE}`]);
        expect(verdict.unneeded.map(pairOf)).toEqual([`light excepted apart ${APART}`]);
        expect(verdict.stale).toEqual(['gone']);
    });

    it('applies an exception in its own theme only: in the other theme the same colour is held to the floor', () => {
        const verdict = guard(IDEAL, 'dark', [{category: 'excepted', colour: BETWEEN}], [{theme: 'light', categories: ['excepted'], recorded: RECORD}]);

        expect(verdict.under.map(pairOf)).toEqual([`dark excepted ${BETWEEN}`]);
        expect([...verdict.closer, ...verdict.unneeded, ...verdict.stale]).toEqual([]);
    });
});
