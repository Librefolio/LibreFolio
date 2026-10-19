/**
 * The fixed colour of every category the charts draw — asset types and sectors — and the two sequences for the charts
 * whose categories have no key of their own. The designer's round 3, her final palette (developer, 17/10/2026, the
 * decisions of `designer-feedback/2026-10-17-round3-grafici`, §1), on the rules of her round 2 (GR1–GR5, D-T17).
 *
 * - **GR1, a colour per key, never per rank.** A category keeps its colour between the pie («Ora») and the history, in
 *   every portfolio, broker and period: `ETF` is the cobalt blue wherever it is drawn.
 * - **No green among the categories (§1.1).** No green, teal, olive, lime or greenish cyan in a type, a sector or a
 *   country: green and red stay the gains' and losses', the brand green the primary actions'. The cash is a slate blue.
 * - **The values are the designer's, as she wrote them.** No two colours of one table are under CIEDE2000 5; the pairs
 *   between 5 and 8 (§1.8) are told apart by the legend and the tooltip, and the distinguishability test names them.
 *
 * The contract with the Designer Lab (C1–C3):
 * - **C1, one read point.** Every chart reads a category colour through {@link categoryColor}: the pie, the history,
 *   their legends and tooltips. The shades of a family (GR4, `./chartShades`) are derived from the colour it returns,
 *   so they follow an edit of it.
 * - **C2, one literal per line.** Each value sits on a line of its own: the Lab exports an edit by file and line. The
 *   sequences name categories ({@link CategoryRef}), never colours: the tables are the only colours of the file.
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

/** The asset-type families, in the designer's table order (§1.2). Subtypes take their family's colour. */
const ASSET_TYPE_COLORS: Readonly<Record<string, ThemePair>> = {
    // violet
    STOCK: {
        light: '#7041C6',
        dark: '#B69AF0',
    },
    // cobalt blue
    ETF: {
        light: '#2459B8',
        dark: '#82ACF8',
    },
    // denim blue
    BOND: {
        light: '#536A9E',
        dark: '#9BAED8',
    },
    // amber, gold
    CRYPTO: {
        light: '#B87916',
        dark: '#E8BD69',
    },
    // indigo (V1-dc)
    FUND: {
        light: '#5147B8',
        dark: '#9280FF',
    },
    // slate (G1-la, G1-db)
    HOLD: {
        light: '#5D687B',
        dark: '#C6D0E0',
    },
    // mauve
    CROWDFUND: {
        light: '#8B547D',
        dark: '#D5A0C7',
    },
    // terracotta
    COMMODITY: {
        light: '#B85E45',
        dark: '#E99A82',
    },
    // bronze, ochre
    REAL_ESTATE: {
        light: '#96602C',
        dark: '#D6A36C',
    },
    // raspberry, orchid
    INDEX: {
        light: '#A33D79',
        dark: '#E58BB9',
    },
    // cool grey
    OTHER: {
        light: '#727B87',
        dark: '#A9B0BB',
    },
};

/** The sectors, in the designer's table order (§1.3). */
const SECTOR_COLORS: Readonly<Record<string, ThemePair>> = {
    // steel, slate (G3-da)
    Industrials: {
        light: '#586579',
        dark: '#ACC6DA',
    },
    // cobalt blue
    Technology: {
        light: '#2459B8',
        dark: '#82ACF8',
    },
    // violet
    Financials: {
        light: '#6748A8',
        dark: '#B9A0EB',
    },
    // orchid, purple
    'Consumer Discretionary': {
        light: '#8B4F9D',
        dark: '#D2A0E0',
    },
    // cerulean
    'Health Care': {
        light: '#2878A8',
        dark: '#7CC0E8',
    },
    // ochre, rust
    'Real Estate': {
        light: '#A45D2A',
        dark: '#DDA16F',
    },
    // brick, terracotta
    'Basic Materials': {
        light: '#A84C36',
        dark: '#E18E7B',
    },
    // amber, gold
    Energy: {
        light: '#B27A16',
        dark: '#E7BD69',
    },
    // dusty mauve
    'Consumer Staples': {
        light: '#8B647A',
        dark: '#C6A2B6',
    },
    // indigo (V1-dc)
    Telecommunication: {
        light: '#5147B8',
        dark: '#9280FF',
    },
    // denim blue
    Utilities: {
        light: '#526F9A',
        dark: '#9CB8E3',
    },
    // plum, raspberry
    'Corporate Bonds': {
        light: '#993D79',
        dark: '#E58BB9',
    },
    // navy (B2-db)
    'Government Bonds': {
        light: '#263F78',
        dark: '#7A93CB',
    },
    // cool grey
    Other: {
        light: '#727B87',
        dark: '#A9B0BB',
    },
};

/** The cash (`Liquidity`), in every grouping: a slate blue, no longer the brand's green (§1.1; B1-dc in dark). */
const LIQUIDITY_COLOR: ThemePair = {
    light: '#3F628C',
    dark: '#639BC0',
};

/**
 * What has no category: the `Unknown` sector and asset type, the `Unknown` and `Other` country. A blue-grey (G2-la,
 * G2-dc).
 */
const UNCLASSIFIED_COLOR: ThemePair = {
    light: '#718C9F',
    dark: '#83939D',
};

/** The keys of each table, in the designer's order, without the two buckets the engine adds. */
export const CATEGORY_KEYS: Readonly<Record<CategoryKind, readonly string[]>> = {
    type: Object.keys(ASSET_TYPE_COLORS),
    sector: Object.keys(SECTOR_COLORS),
};

/** The buckets the portfolio engine adds beside the types and the sectors: the cash, and what has no category. */
export const CATEGORY_BUCKETS: readonly string[] = ['Liquidity', 'Unknown'];

/** A category of one of the two tables, as a sequence lists it: its colour is read from the table, never copied. */
export interface CategoryRef {
    readonly kind: CategoryKind;
    readonly key: string;
}

function typeRef(key: string): CategoryRef {
    return {kind: 'type', key};
}

function sectorRef(key: string): CategoryRef {
    return {kind: 'sector', key};
}

/**
 * The first eight asset types of the designer's table, in its order (§1.5): the categories that have an order but no
 * key of their own — the owners of the semi-donut, the broker lines of the Growth chart. Read with
 * {@link sequenceColor}.
 */
export const CATEGORY_SEQUENCE: readonly CategoryRef[] = ['STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND', 'HOLD', 'CROWDFUND', 'COMMODITY'].map((key) => typeRef(key));

/**
 * The countries of the geography history, by rank among the classified ones (§1.4): fourteen categories of the two
 * tables, so a country follows the designer's choice for the colour it shares with a type or a sector. Where a type
 * and a sector have the same colour, the type. The unclassified countries keep their own colour
 * ({@link isUnclassifiedCountry}). Read with {@link sequenceColor}.
 */
export const COUNTRY_SEQUENCE: readonly CategoryRef[] = [
    typeRef('ETF'),
    typeRef('STOCK'),
    sectorRef('Basic Materials'),
    sectorRef('Energy'),
    sectorRef('Health Care'),
    sectorRef('Corporate Bonds'),
    sectorRef('Utilities'),
    sectorRef('Consumer Discretionary'),
    sectorRef('Real Estate'),
    typeRef('FUND'),
    typeRef('HOLD'),
    sectorRef('Consumer Staples'),
    sectorRef('Government Bonds'),
    typeRef('OTHER'),
];

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
 * The colour of the category ranked `rank` (0-based) in a sequence (GR5): the sequence in order, then the same sequence
 * one shade further at each round (`familyShade`), never a silent repeat. A sequence of 14 gives 98 distinct colours
 * before they cycle. Each colour is read through {@link categoryColor}, so it follows an edit of its table (C1).
 */
export function sequenceColor(sequence: readonly CategoryRef[], rank: number, dark: boolean, poles: ShadePoles): string {
    const {kind, key} = sequence[rank % sequence.length];
    return familyShade(categoryColor(kind, key, dark), Math.floor(rank / sequence.length), poles);
}

/** Whether a country key is the unclassified one of the geography: the engine's `Unknown`, or a provider's `Other`. */
export function isUnclassifiedCountry(key: string): boolean {
    const normalised = lookupKey(key);
    return normalised === 'UNKNOWN' || normalised === 'OTHER';
}
