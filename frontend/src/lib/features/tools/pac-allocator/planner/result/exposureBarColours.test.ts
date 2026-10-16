// @vitest-environment node
/**
 * exposureBarColours — the colours of the PAC's exposure bars, «ideal vs actual» (TD-1, R9.8; the coordinator,
 * 15/10/2026).
 *
 * - **The actual weight** takes its row's category colour, the dashboard's (GR1), in the order of the rows:
 *   - a sector its colour by key;
 *   - an Asset type its family's colour, and a subtype a shade of it, ranked as in the pie's outer ring (GR4): the
 *     generic member keeps the family's colour; the subtypes take `familyShade` by rank among their own family's
 *     subtypes, largest ideal weight first (`compareExact`, exact across a decimal and a ratio), ties by id. A subtype
 *     never takes the family's own colour, even with no generic member beside it;
 *   - the uncategorised remainder, in either dimension, the unclassified bucket (`Unknown`); a type outside the table
 *     (`warrant`) the unclassified colour too.
 * - **The ideal weight** reads the secondary text role (`idealColour`), shown with an injected role reader.
 * - **The ΔE00 guard** (the coordinator's decision). The ideal, as the charts read it where no page sets the role (the
 *   stand-ins), stays at least ΔE00 10 from every category colour — each key of both tables and both buckets, in both
 *   themes — so a row's colour belongs to its actual weight alone. One recorded exception: the «Other» grey that
 *   `OTHER` and `Other` share, dark theme, recorded at 9.0 (measured 9.05). The guard fails if that pair drops below its
 *   record, if any other pair goes under 10, and if the exception is no longer needed, so it does not outlive its
 *   reason. The ruler is `$test/colorDistance`, checked on published data first; every red path is shown on synthetic
 *   colours.
 *
 * Every expected colour is computed from the public functions (`categoryColor`, `familyShade`), never copied: the
 * values are the designer's, the rule is this module's. Exact weights are written as `model.test.ts` writes them.
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

import {ciede2000, deltaE00, SHARMA_PAIRS} from '$test/colorDistance';
import {CATEGORY_BUCKETS, CATEGORY_KEYS, categoryColor, type CategoryKind} from '$lib/theme/chartCategories';
import {familyShade, shadePoles, type ShadePoles} from '$lib/theme/chartShades';
import {chartRoles, type RoleReader, setRoleReader} from '$lib/theme/roleColors';
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

describe('idealColour — the secondary text role', () => {
    it('reads --lf-text-secondary, and no other role, from the roles it is handed', () => {
        const reader = vi.fn<RoleReader>((role) => (role === '--lf-text-secondary' ? '#123456' : ''));
        setRoleReader(reader);

        expect(idealColour(chartRoles(false, null))).toBe('#123456');
        expect(reader.mock.calls.map(([role]) => role)).toEqual(['--lf-text-secondary']);
    });
});

// =============================================================================
// The ΔE00 guard — the ideal apart from every category colour
// =============================================================================

type Theme = (typeof THEMES)[number][0];

/** Under this distance two colours side by side are confused (`analisi.md` §4): the coordinator's floor for TD-1. */
const FLOOR = 10;

/** A pair allowed under the floor, in one theme, at no less than its recorded distance. */
interface Exception {
    theme: Theme;
    /** The categories carrying the excepted colour, as `categoryColours` names them. */
    categories: readonly string[];
    recorded: number;
}

/** The one recorded exception (TD-1): the «Other» grey that OTHER and Other share, dark theme, measured 9.05. */
const OTHER_GREY: Exception = {theme: 'dark', categories: ['type OTHER', 'sector Other'], recorded: 9.0};

/** Every category colour of a theme: each key of both tables, and the two buckets both tables share. */
function categoryColours(dark: boolean): Array<{category: string; colour: string}> {
    const kinds: readonly CategoryKind[] = ['type', 'sector'];
    const keyed = kinds.flatMap((kind) => CATEGORY_KEYS[kind].map((key) => ({category: `${kind} ${key}`, colour: categoryColor(kind, key, dark)})));
    return [...keyed, ...CATEGORY_BUCKETS.map((key) => ({category: `bucket ${key}`, colour: categoryColor('type', key, dark)}))];
}

interface GuardVerdict {
    /** How many category colours were measured. */
    measured: number;
    /** Pairs under the floor that the exception does not cover. */
    under: string[];
    /** Excepted pairs now closer than recorded. */
    closer: string[];
    /** Excepted pairs now at the floor or past it: the exception has outlived its reason. */
    unneeded: string[];
    /** Excepted categories the measure never met. */
    stale: string[];
}

/** The ideal of `theme` measured against every colour, and judged against the floor and the exception. */
function guard(ideal: string, theme: Theme, colours: ReadonlyArray<{category: string; colour: string}>, exception: Exception): GuardVerdict {
    const excepted = exception.theme === theme ? exception.categories : [];
    const verdict: GuardVerdict = {measured: 0, under: [], closer: [], unneeded: [], stale: excepted.filter((category) => !colours.some((entry) => entry.category === category))};
    for (const {category, colour} of colours) {
        verdict.measured += 1;
        const distance = deltaE00(ideal, colour);
        const shown = `${theme} ${category} ${colour}: ΔE00 ${distance.toFixed(2)} from the ideal ${ideal}`;
        if (!excepted.includes(category)) {
            if (distance < FLOOR) verdict.under.push(shown);
        } else if (distance >= FLOOR) {
            verdict.unneeded.push(shown);
        } else if (distance < exception.recorded) {
            verdict.closer.push(`${shown}, recorded ${exception.recorded.toFixed(1)}`);
        }
    }
    return verdict;
}

/** The pair a verdict line names, without its measure. */
const pairOf = (line: string): string => line.split(':')[0];

describe('the ΔE00 guard — the ideal stays apart from every category colour (TD-1)', () => {
    it.each(THEMES)('%s: at least ΔE00 10 from every type, sector and bucket, but the recorded «Other» grey', (theme, dark) => {
        const ideal = idealColour(chartRoles(dark, null));
        const verdict = guard(ideal, theme, categoryColours(dark), OTHER_GREY);

        expect(verdict.measured, 'barrier: every key of both tables and both buckets was measured').toBe(CATEGORY_KEYS.type.length + CATEGORY_KEYS.sector.length + CATEGORY_BUCKETS.length);
        expect(verdict.stale, 'the exception names a category the tables no longer have: record it again').toEqual([]);
        expect(verdict.under, `these category colours are closer than ΔE00 ${FLOOR} to the ideal weight: its bar would read as that category`).toEqual([]);
        expect(verdict.closer, 'the «Other» grey is closer to the ideal than recorded: the values moved toward each other').toEqual([]);
        expect(verdict.unneeded, `the «Other» grey is now at least ΔE00 ${FLOOR} from the ideal: remove the exception`).toEqual([]);
    });

    it('positive control: the ruler reproduces the published CIEDE2000 data, and the guard meets the recorded pair where it is', () => {
        const misses = SHARMA_PAIRS.filter(({first, second, deltaE}) => Math.abs(ciede2000(first, second) - deltaE) > 1e-4).map(({pair}) => pair);
        expect(misses, 'pairs of Sharma, Wu & Dalal (2005) the ruler does not reproduce').toEqual([]);

        // The ideal is the role as the charts read it, here the stand-in, and the one exception is one colour.
        const ideal = idealColour(chartRoles(true, null));
        expect(ideal).toBe(chartRoles(true, null).color('--lf-text-secondary'));
        const colours = categoryColours(true);
        const excepted = colours.filter(({category}) => OTHER_GREY.categories.includes(category));
        expect(new Set(excepted.map(({colour}) => colour.toUpperCase())).size, 'OTHER and Other carry one colour').toBe(1);

        // The closest category colours to the dark ideal are that pair, between their record and the floor.
        const closest = colours.map(({category, colour}) => ({category, distance: deltaE00(ideal, colour)})).sort((a, b) => a.distance - b.distance);
        expect(
            closest.slice(0, OTHER_GREY.categories.length).map(({category}) => category),
            'the closest colours the guard meets',
        ).toEqual(expect.arrayContaining([...OTHER_GREY.categories]));
        for (const {distance} of closest.slice(0, OTHER_GREY.categories.length)) {
            expect(distance).toBeGreaterThanOrEqual(OTHER_GREY.recorded);
            expect(distance).toBeLessThan(FLOOR);
        }
    });
});

describe('the ΔE00 guard — each red path, on synthetic colours', () => {
    /** A synthetic ideal and its neighbours, at the distances the cases need (checked below). */
    const IDEAL = '#808080';
    const NEAR = '#868686';
    const FAR = '#ff0000';
    const TOO_CLOSE = '#959595';
    const BETWEEN = '#9c9c9c';
    const APART = '#a0a0a0';

    it('premise: the synthetic colours sit where the cases need them', () => {
        expect(deltaE00(IDEAL, NEAR), 'under the floor').toBeLessThan(FLOOR);
        expect(deltaE00(IDEAL, FAR), 'past the floor').toBeGreaterThanOrEqual(FLOOR);
        expect(deltaE00(IDEAL, TOO_CLOSE), 'under the record').toBeLessThan(OTHER_GREY.recorded);
        expect(deltaE00(IDEAL, BETWEEN), 'between the record and the floor').toBeGreaterThanOrEqual(OTHER_GREY.recorded);
        expect(deltaE00(IDEAL, BETWEEN), 'between the record and the floor').toBeLessThan(FLOOR);
        expect(deltaE00(IDEAL, APART), 'past the floor').toBeGreaterThanOrEqual(FLOOR);
    });

    it('passes a clean measure: every pair past the floor, the excepted one between its record and the floor', () => {
        const colours = [
            {category: 'clean', colour: FAR},
            {category: 'excepted', colour: BETWEEN},
        ];
        const verdict = guard(IDEAL, 'dark', colours, {theme: 'dark', categories: ['excepted'], recorded: OTHER_GREY.recorded});

        expect(verdict).toEqual({measured: 2, under: [], closer: [], unneeded: [], stale: []});
    });

    it('names a pair under the floor it does not cover, an excepted pair closer than recorded, one no longer needed, and one it never met', () => {
        const colours = [
            {category: 'near', colour: NEAR},
            {category: 'clean', colour: FAR},
            {category: 'excepted close', colour: TOO_CLOSE},
            {category: 'excepted apart', colour: APART},
        ];
        const verdict = guard(IDEAL, 'dark', colours, {theme: 'dark', categories: ['excepted close', 'excepted apart', 'gone'], recorded: OTHER_GREY.recorded});

        expect(verdict.measured).toBe(4);
        expect(verdict.under.map(pairOf)).toEqual([`dark near ${NEAR}`]);
        expect(verdict.closer.map(pairOf)).toEqual([`dark excepted close ${TOO_CLOSE}`]);
        expect(verdict.unneeded.map(pairOf)).toEqual([`dark excepted apart ${APART}`]);
        expect(verdict.stale).toEqual(['gone']);
    });

    it('applies the exception in its own theme only: in the other theme the same pair is held to the floor', () => {
        const verdict = guard(IDEAL, 'light', [{category: 'excepted', colour: BETWEEN}], {theme: 'dark', categories: ['excepted'], recorded: OTHER_GREY.recorded});

        expect(verdict.under.map(pairOf)).toEqual([`light excepted ${BETWEEN}`]);
        expect([...verdict.closer, ...verdict.unneeded, ...verdict.stale]).toEqual([]);
    });
});
