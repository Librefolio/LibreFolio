/**
 * The fixed colour of every category the charts draw — asset types and sectors — and the two sequences for the charts
 * whose categories have no fixed colour. The designer's round 2, GR1–GR5, approved by the developer (D-T17,
 * 15/10/2026).
 *
 * - **GR1, a colour per key, never per rank.** A category keeps its colour between the pie («Ora») and the history, in
 *   every portfolio, broker and period: `ETF` is the cobalt blue wherever it is drawn.
 * - **GR2, no semantic red or green.** Loss red and gain green stay out of the categories; the brand green is the
 *   cash's alone (GR3).
 * - **The values are the designer's, as she wrote them.** The pairs measured close (CIEDE2000 under 10, the round-2
 *   analysis §4) go back to her in round 3: the distinguishability test lists them, nothing here corrects them.
 *
 * The contract with the Designer Lab (C1–C3, round 3):
 * - **C1, one read point.** Every chart reads a category colour through {@link categoryColor}: the pie, the history,
 *   their legends and tooltips. The shades of a family (GR4, `./chartShades`) are derived from the colour it returns,
 *   so they follow an edit of it.
 * - **C2, one literal per line.** Each value sits on a line of its own: the Lab exports an edit by file and line.
 * - **C3, a hook in debug builds only.** {@link categoryColor} first asks the Lab for an edited colour; a release
 *   build drops that branch, and the app imports nothing of the Lab.
 *
 * Keys arrive as the backend writes them: asset types upper case (`ETF`, `CROWDFUND`…), sectors as `FinancialSector`
 * values (`"Health Care"`), each beside the engine's two buckets, `"Liquidity"` and `"Unknown"`. The lookup ignores
 * case, spaces and underscores ({@link lookupKey}, exported so the Designer Lab keys its edits the same way). A subtype
 * (`ETF_STOCK`) is resolved to its family by the caller, with `assetTypeFamily`: importing `$lib/utils/assetTypes` here
 * would drag the generated API client into every consumer.
 *
 * @module lib/theme/chartCategories
 */

import {familyShade, type ShadePoles} from './chartShades';
import {themed, type ThemePair} from './themePair';

/** The two kinds of category with a fixed colour. */
export type CategoryKind = 'type' | 'sector';

/** The asset-type families, in the designer's table order (table 3.2 A). Subtypes take their family's colour. */
const ASSET_TYPE_COLORS: Readonly<Record<string, ThemePair>> = {
    // amethyst violet
    STOCK: {
        light: '#6D28D9',
        dark: '#A78BFA',
    },
    // cobalt blue
    ETF: {
        light: '#1D5BD8',
        dark: '#60A5FA',
    },
    // petrol
    BOND: {
        light: '#0E7490',
        dark: '#22D3EE',
    },
    // amber, gold
    CRYPTO: {
        light: '#D97706',
        dark: '#FBBF24',
    },
    // indigo
    FUND: {
        light: '#4338CA',
        dark: '#818CF8',
    },
    // slate blue
    HOLD: {
        light: '#5F6B7A',
        dark: '#94A3B8',
    },
    // teal
    CROWDFUND: {
        light: '#0D9488',
        dark: '#2DD4BF',
    },
    // copper, terracotta
    COMMODITY: {
        light: '#C25E00',
        dark: '#FB923C',
    },
    // ochre, brick
    REAL_ESTATE: {
        light: '#B45309',
        dark: '#F59E0B',
    },
    // plum, orchid
    INDEX: {
        light: '#A21CAF',
        dark: '#E879F9',
    },
    // stone grey
    OTHER: {
        light: '#6E7A74',
        dark: '#7F8C87',
    },
};

/** The sectors, in the designer's table order (table 3.2 B). */
const SECTOR_COLORS: Readonly<Record<string, ThemePair>> = {
    // steel, slate
    Industrials: {
        light: '#475569',
        dark: '#94A3B8',
    },
    // cobalt blue
    Technology: {
        light: '#1D5BD8',
        dark: '#60A5FA',
    },
    // teal
    Financials: {
        light: '#0F766E',
        dark: '#2DD4BF',
    },
    // violet
    'Consumer Discretionary': {
        light: '#7C3AED',
        dark: '#A78BFA',
    },
    // cerulean
    'Health Care': {
        light: '#0284C7',
        dark: '#38BDF8',
    },
    // ochre, amber
    'Real Estate': {
        light: '#B45309',
        dark: '#FBBF24',
    },
    // terracotta, copper
    'Basic Materials': {
        light: '#9A3412',
        dark: '#FB923C',
    },
    // gold, yellow
    Energy: {
        light: '#D97706',
        dark: '#FACC15',
    },
    // olive, lime
    'Consumer Staples': {
        light: '#4D7C0F',
        dark: '#A3E635',
    },
    // indigo
    Telecommunication: {
        light: '#4338CA',
        dark: '#818CF8',
    },
    // petrol
    Utilities: {
        light: '#0E7490',
        dark: '#22D3EE',
    },
    // plum
    'Corporate Bonds': {
        light: '#86198F',
        dark: '#E879F9',
    },
    // navy
    'Government Bonds': {
        light: '#1E3A8A',
        dark: '#93C5FD',
    },
    // stone grey
    Other: {
        light: '#6E7A74',
        dark: '#7F8C87',
    },
};

/** The cash (`Liquidity`), in every grouping: the brand's sage green, its alone (GR3). */
const LIQUIDITY_COLOR: ThemePair = {
    light: '#2D6A54',
    dark: '#429E79',
};

/** What has no category: the `Unknown` sector and asset type, the `Unknown` and `Other` country. A fog grey. */
const UNCLASSIFIED_COLOR: ThemePair = {
    light: '#94A09B',
    dark: '#52605B',
};

/** The keys of each table, in the designer's order, without the two buckets the engine adds. */
export const CATEGORY_KEYS: Readonly<Record<CategoryKind, readonly string[]>> = {
    type: Object.keys(ASSET_TYPE_COLORS),
    sector: Object.keys(SECTOR_COLORS),
};

/** The buckets the portfolio engine adds beside the types and the sectors: the cash, and what has no category. */
export const CATEGORY_BUCKETS: readonly string[] = ['Liquidity', 'Unknown'];

/**
 * The first eight asset types of the designer's table: the categories that have an order but no key of their own —
 * the owners of the semi-donut, the broker lines of the Growth chart (GR5.2). Read with {@link sequenceColor}.
 */
export const CATEGORY_SEQUENCE: readonly string[] = ['STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND', 'HOLD', 'CROWDFUND', 'COMMODITY'];

/**
 * The fourteen sectors of the designer's table, in its order: the categories ranked without a fixed colour, the
 * countries of the geography history (GR5). The unclassified ones keep their own colour. Read with
 * {@link sequenceColor}.
 */
export const KEYLESS_SEQUENCE: readonly string[] = CATEGORY_KEYS.sector;

/** A key as the lookup compares it: case, spaces and underscores ignored (`Health Care`, `HEALTH_CARE`, `healthcare`). */
export function lookupKey(key: string): string {
    return key.replace(/[\s_]/g, '').toUpperCase();
}

function lookupTable(table: Readonly<Record<string, ThemePair>>): Map<string, ThemePair> {
    const entries: [string, ThemePair][] = [...Object.entries(table), ['Liquidity', LIQUIDITY_COLOR], ['Unknown', UNCLASSIFIED_COLOR]];
    return new Map(entries.map(([key, pair]) => [lookupKey(key), pair]));
}

const LOOKUP: Readonly<Record<CategoryKind, Map<string, ThemePair>>> = {
    type: lookupTable(ASSET_TYPE_COLORS),
    sector: lookupTable(SECTOR_COLORS),
};

/** What the Designer Lab may answer for a category, in a debug build (C3): an edited colour, or nothing. */
interface CategoryColorEditor {
    categoryColor?: (kind: CategoryKind, key: string, dark: boolean) => string | null | undefined;
}

/**
 * The colour of a category in the active theme: the one read point of the charts (C1).
 *
 * `type` takes an asset-type family (a subtype is resolved first, with `assetTypeFamily`), `sector` a sector; both
 * take the `Liquidity` and `Unknown` buckets. A key outside the tables reads as unclassified: the enum gates keep that
 * case out of the real data.
 */
export function categoryColor(kind: CategoryKind, key: string, dark: boolean): string {
    // `typeof` first: Vitest has no `define`, and the bare name would throw there. A release build turns the whole
    // condition into `false` and its minifier drops the branch (C3).
    if (typeof __LF_DESIGNER_LAB__ !== 'undefined' && __LF_DESIGNER_LAB__) {
        const edited = (globalThis as unknown as {__lfDesignerLab?: CategoryColorEditor}).__lfDesignerLab?.categoryColor?.(kind, key, dark);
        if (edited) return edited;
    }
    return themed(LOOKUP[kind].get(lookupKey(key)) ?? UNCLASSIFIED_COLOR, dark);
}

/**
 * The colour of the category ranked `rank` (0-based) in a sequence of keys of `kind` (GR5): the sequence in order,
 * then the same sequence one shade further at each round (`familyShade`), never a silent repeat. A sequence of 14
 * gives 98 distinct colours before they cycle.
 */
export function sequenceColor(kind: CategoryKind, sequence: readonly string[], rank: number, dark: boolean, poles: ShadePoles): string {
    const count = sequence.length;
    return familyShade(categoryColor(kind, sequence[rank % count], dark), Math.floor(rank / count), poles);
}

/** Whether a country key is the unclassified one of the geography: the engine's `Unknown`, or a provider's `Other`. */
export function isUnclassifiedCountry(key: string): boolean {
    const normalised = lookupKey(key);
    return normalised === 'UNKNOWN' || normalised === 'OTHER';
}
