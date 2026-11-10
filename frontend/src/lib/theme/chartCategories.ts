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
 * - **The asset types and the cash are roles (DV-11, 22/10/2026).** Their colours are the roles `--lf-cat-*` of
 *   tokens.css, which the badges read too: one copy, no longer two held equal by a test. {@link CATEGORY_ROLES} names
 *   them; the Lab shows each as a view of its role and edits the role (L1), so an edit reaches the badges and the
 *   charts together. The sectors and «Unknown» have no roles yet: they stay literals of this file.
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
import {type ChartRole, chartRoles, pageRoles} from './roleColors';
import {themed, type ThemePair} from './themePair';

/** The two kinds of category with a fixed colour. */
export type CategoryKind = 'type' | 'sector';

/**
 * The asset-type families, in the designer's table order (§1.2), each on its role of tokens.css (`--lf-cat-*`, §1.9):
 * the badges and the charts read one colour (DV-11), and the Designer Lab edits it as that role. Subtypes take their
 * family's colour. The role is read through `pageRoles` (`./roleColors`) at each ask.
 */
const ASSET_TYPE_ROLES = {
    STOCK: '--lf-cat-stock', // violet
    ETF: '--lf-cat-etf', // cobalt blue
    BOND: '--lf-cat-bond', // denim blue
    CRYPTO: '--lf-cat-crypto', // amber, gold
    FUND: '--lf-cat-fund', // indigo (V1-dc)
    HOLD: '--lf-cat-hold', // slate (G1-la, G1-db)
    CROWDFUND: '--lf-cat-crowdfund', // mauve
    COMMODITY: '--lf-cat-commodity', // terracotta
    REAL_ESTATE: '--lf-cat-real-estate', // bronze, ochre
    INDEX: '--lf-cat-index', // raspberry, orchid
    OTHER: '--lf-cat-other', // cool grey
} as const satisfies Readonly<Record<string, ChartRole>>;

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

/** The cash (`Liquidity`), in every grouping: a slate blue, no longer the brand's green (§1.1; B1-dc in dark). Its role. */
const LIQUIDITY_ROLE: ChartRole = '--lf-cat-liquidity';

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
    type: Object.keys(ASSET_TYPE_ROLES),
    sector: Object.keys(SECTOR_COLORS),
};

/** The buckets the portfolio engine adds beside the types and the sectors: the cash, and what has no category. */
export const CATEGORY_BUCKETS: readonly string[] = ['Liquidity', 'Unknown'];

/** A category whose colour is a role of tokens.css, not a line of this file: the asset types and the cash (DV-11). */
export interface CategoryRole {
    /** `type:ETF`, `bucket:Liquidity`: the target the Designer Lab names the category by. */
    readonly target: string;
    readonly kind: 'type' | 'bucket';
    readonly key: string;
    /** The role the category is drawn in, the one the Designer Lab edits. */
    readonly role: ChartRole;
}

/** The categories drawn in a role, in the table's order, the cash last: what the Designer Lab shows as views of the roles. */
export const CATEGORY_ROLES: readonly CategoryRole[] = [...Object.entries(ASSET_TYPE_ROLES).map(([key, role]): CategoryRole => ({target: `type:${key}`, kind: 'type', key, role})), {target: 'bucket:Liquidity', kind: 'bucket', key: 'Liquidity', role: LIQUIDITY_ROLE}];

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

/** Where a category's colour comes from: a pair of this file, or a role of tokens.css. */
type CategorySource = ThemePair | ChartRole;

function lookupTable(table: Readonly<Record<string, CategorySource>>): Map<string, CategorySource> {
    const entries: [string, CategorySource][] = [...Object.entries(table), ['Liquidity', LIQUIDITY_ROLE], ['Unknown', UNCLASSIFIED_COLOR]];
    return new Map(entries.map(([key, source]) => [lookupKey(key), source]));
}

const LOOKUP: Readonly<Record<CategoryKind, Map<string, CategorySource>>> = {
    type: lookupTable(ASSET_TYPE_ROLES),
    sector: lookupTable(SECTOR_COLORS),
};

/** The colour of a source in a theme: a role read now (`pageRoles`), or the member of a pair. */
function sourceColor(source: CategorySource, dark: boolean, scope?: Element | null): string {
    if (typeof source !== 'string') return themed(source, dark);
    return (scope ? chartRoles(dark, scope) : pageRoles(dark)).color(source);
}

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
 *
 * `scope` is the chart's own element: a role (an asset type, the cash) is read there, as `chartRoles` reads every role
 * of a chart, so a chart inside a forced `.light`/`.dark` subtree reads its own theme. Without it, the page's
 * (`pageRoles`): `<html>` when it shows the theme asked, the stand-ins otherwise.
 */
export function categoryColor(kind: CategoryKind, key: string, dark: boolean, scope?: Element | null): string {
    // `typeof` first: Vitest has no `define`, and the bare name would throw there. A release build turns the whole
    // condition into `false` and its minifier drops the branch (C3).
    if (typeof __LF_DESIGNER_LAB__ !== 'undefined' && __LF_DESIGNER_LAB__) {
        const edited = (globalThis as unknown as {__lfDesignerLab?: CategoryColorEditor}).__lfDesignerLab?.categoryColor?.(kind, key, dark);
        if (edited) return edited;
    }
    return sourceColor(LOOKUP[kind].get(lookupKey(key)) ?? UNCLASSIFIED_COLOR, dark, scope);
}

/**
 * The colour of the category ranked `rank` (0-based) in a sequence (GR5): the sequence in order, then the same sequence
 * one shade further at each round (`familyShade`), never a silent repeat. A sequence of 14 gives 98 distinct colours
 * before they cycle. Each colour is read through {@link categoryColor}, so it follows an edit of its table (C1).
 */
export function sequenceColor(sequence: readonly CategoryRef[], rank: number, dark: boolean, poles: ShadePoles, scope?: Element | null): string {
    const {kind, key} = sequence[rank % sequence.length];
    return familyShade(categoryColor(kind, key, dark, scope), Math.floor(rank / sequence.length), poles);
}

/** Whether a country key is the unclassified one of the geography: the engine's `Unknown`, or a provider's `Other`. */
export function isUnclassifiedCountry(key: string): boolean {
    const normalised = lookupKey(key);
    return normalised === 'UNKNOWN' || normalised === 'OTHER';
}
