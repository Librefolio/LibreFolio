/**
 * Asset Types — Centralized utility for asset type constants, icon mapping, and option builders.
 *
 * Replaces duplicated ASSET_TYPE_PNG_MAP in AssetIcon, AssetModal, AssetTable, ProviderAssignmentSection.
 * Single source of truth for asset type enums, identifier types, and their UI representation.
 * Enum values are derived from Zod schemas in generated.ts (auto-generated from backend).
 *
 * @module utils/assetTypes
 */

import {schemas} from '$lib/api/generated';
import type {TreeSelectGroup, TreeSelectItem} from '$lib/components/ui/select/treeSelect';

// =============================================================================
// ASSET TYPES — derived from backend enum via Zod schema
// =============================================================================

export const ASSET_TYPES = schemas.AssetType.options;

/**
 * Map asset type code → PNG filename in /icons/asset-types/.
 *
 * A subtype is drawn with a **composite**: the icon of the family it belongs to, whole, with a
 * small pastille in the corner showing what it contains — `etf-stock` is the ETF tag with the
 * stock pastille (decision D52, delivered as R16). The container keeps saying what the
 * instrument *is* (a fund you buy on an exchange), so an equity ETF never looks like a share;
 * the pastille says what it holds, which the label alone used to say.
 *
 * The composites are generated, never hand-drawn: `scripts/compose_asset_type_icons.py` reads
 * this map, {@link ASSET_TYPE_FAMILY} and {@link ASSET_TYPE_CONTENT_ICON} as text and writes
 * `{family file}-{content file}.png`. The file name of a subtype here must follow that rule; the
 * script refuses to run otherwise, and `assetTypeTables.test.ts` checks the files exist.
 */
const PNG_MAP: Record<string, string> = {
    STOCK: 'stock',
    ETF: 'etf',
    BOND: 'bond',
    CRYPTO: 'crypto',
    FUND: 'fund',
    HOLD: 'hold',
    CROWDFUND: 'crowdfunding',
    COMMODITY: 'commodity',
    REAL_ESTATE: 'real-estate',
    INDEX: 'index',
    OTHER: 'other',
    LIQUIDITY: 'liquidity',
    ETF_STOCK: 'etf-stock',
    ETF_BOND: 'etf-bond',
    ETF_COMMODITY: 'etf-commodity',
    ETF_REAL_ESTATE: 'etf-real-estate',
    ETF_CRYPTO: 'etf-crypto',
    ETF_MONETARY: 'etf-liquidity',
    CROWDFUND_REAL_ESTATE: 'crowdfunding-real-estate',
};

/**
 * Subtype → the family (container) it specialises. Types not listed are their own family.
 *
 * This is the **container** view — "which kind of instrument is it?" — and it is deliberately a
 * different relation from {@link primaryAssetType}, which is the **content** view: `ETF_STOCK`
 * belongs to the `ETF` family and contains `STOCK`. The select and both allocation charts — the
 * pie and, since I's D15, the history chart — group by family. One map per question, never two
 * maps of the same one.
 */
export const ASSET_TYPE_FAMILY: Readonly<Record<string, string>> = {
    ETF_STOCK: 'ETF',
    ETF_BOND: 'ETF',
    ETF_COMMODITY: 'ETF',
    ETF_REAL_ESTATE: 'ETF',
    ETF_CRYPTO: 'ETF',
    ETF_MONETARY: 'ETF',
    CROWDFUND_REAL_ESTATE: 'CROWDFUND',
};

/**
 * Subtype → PNG filename of the pastille that says what it contains — the "second constant next
 * to `PNG_MAP`" of decision D52.
 *
 * The rule (D61) is mechanical: the pastille is the icon of the base type the subtype contains,
 * i.e. `PNG_MAP[primaryAssetType(x)]`. The single exception is `ETF_MONETARY` (D67): a money
 * market fund has no base type to roll up to, and borrows `liquidity` because it means money
 * without being an asset type. Written out rather than derived so that the exception is visible
 * here instead of hiding in a branch; the gate test holds it to the rule.
 */
const ASSET_TYPE_CONTENT_ICON: Record<string, string> = {
    ETF_STOCK: 'stock',
    ETF_BOND: 'bond',
    ETF_COMMODITY: 'commodity',
    ETF_REAL_ESTATE: 'real-estate',
    ETF_CRYPTO: 'crypto',
    ETF_MONETARY: 'liquidity',
    CROWDFUND_REAL_ESTATE: 'real-estate',
};

/**
 * Badge colour per asset type, on the categorical roles of `tokens.css` (designer, round 3, §1.9: A1-a and column F,
 * 17/10): the tint of the type, `--lf-cat-<type>-soft`, and its badge text, `--lf-cat-<type>-on-soft` — the colour
 * the charts draw the type in.
 *
 * A subtype takes the colour of its **family**, what it is (`ETF_STOCK` is an ETF: the ETF's blue), and says what
 * it **contains** with a dot, like the pastille of its icon ({@link assetTypeBadgeDotClass}). The dot is in the
 * content's badge text colour, `--lf-cat-<content>-on-soft`: the same hue, darker in light where her badge table
 * darkens it, so it stands at 4.30:1 at least on the family's tint, where the content's own colour gave
 * ETF_CRYPTO 2.84:1 in light, under her 3:1 for icons (decided with the coordinator, 17/10).
 * The invariants, held by the enum gate test: `BADGE_CLASS_MAP[x] === BADGE_CLASS_MAP[assetTypeFamily(x)]`, and a
 * subtype's dot is the role of `ASSET_TYPE_CONTENT_ICON[x]` — the liquidity of `ETF_MONETARY` included.
 *
 * This lives here, not in a component, because three views render the same badge (`AssetTable`'s HTML cell,
 * `AssetCard`'s markup and `ProviderComparisonModal`). They used to carry one hand-written map each, and the two
 * first had already drifted apart. The enum gate test reads *these* maps.
 */
const BADGE_CLASS_MAP: Record<string, string> = {
    STOCK: 'bg-lf-cat-stock-soft text-lf-cat-stock-on-soft',
    ETF: 'bg-lf-cat-etf-soft text-lf-cat-etf-on-soft',
    BOND: 'bg-lf-cat-bond-soft text-lf-cat-bond-on-soft',
    CRYPTO: 'bg-lf-cat-crypto-soft text-lf-cat-crypto-on-soft',
    FUND: 'bg-lf-cat-fund-soft text-lf-cat-fund-on-soft',
    HOLD: 'bg-lf-cat-hold-soft text-lf-cat-hold-on-soft',
    CROWDFUND: 'bg-lf-cat-crowdfund-soft text-lf-cat-crowdfund-on-soft',
    COMMODITY: 'bg-lf-cat-commodity-soft text-lf-cat-commodity-on-soft',
    REAL_ESTATE: 'bg-lf-cat-real-estate-soft text-lf-cat-real-estate-on-soft',
    INDEX: 'bg-lf-cat-index-soft text-lf-cat-index-on-soft',
    // Explicit, not left to the fallback: an OTHER asset is a deliberate
    // classification and must not look identical to a type nobody mapped.
    OTHER: 'bg-lf-cat-other-soft text-lf-cat-other-on-soft',
    // Not an AssetType: the cash bucket the backend adds; slate blue, never green (§1.1).
    LIQUIDITY: 'bg-lf-cat-liquidity-soft text-lf-cat-liquidity-on-soft',
    // The subtypes, in their family's colour; their content is the dot.
    ETF_STOCK: 'bg-lf-cat-etf-soft text-lf-cat-etf-on-soft',
    ETF_BOND: 'bg-lf-cat-etf-soft text-lf-cat-etf-on-soft',
    ETF_COMMODITY: 'bg-lf-cat-etf-soft text-lf-cat-etf-on-soft',
    ETF_REAL_ESTATE: 'bg-lf-cat-etf-soft text-lf-cat-etf-on-soft',
    ETF_CRYPTO: 'bg-lf-cat-etf-soft text-lf-cat-etf-on-soft',
    ETF_MONETARY: 'bg-lf-cat-etf-soft text-lf-cat-etf-on-soft',
    CROWDFUND_REAL_ESTATE: 'bg-lf-cat-crowdfund-soft text-lf-cat-crowdfund-on-soft',
};

/** A subtype's dot, in the colour of what it contains (written whole, so the colour gates and Tailwind see it). */
const BADGE_DOT_CLASS_MAP: Record<string, string> = {
    ETF_STOCK: 'bg-lf-cat-stock-on-soft',
    ETF_BOND: 'bg-lf-cat-bond-on-soft',
    ETF_COMMODITY: 'bg-lf-cat-commodity-on-soft',
    ETF_REAL_ESTATE: 'bg-lf-cat-real-estate-on-soft',
    ETF_CRYPTO: 'bg-lf-cat-crypto-on-soft',
    ETF_MONETARY: 'bg-lf-cat-liquidity-on-soft',
    CROWDFUND_REAL_ESTATE: 'bg-lf-cat-real-estate-on-soft',
};

/** The neutral chip for a type nobody mapped. The gate test exists so it never shows. */
const BADGE_CLASS_FALLBACK = 'bg-lf-neutral text-lf-secondary';

/** Role classes for an asset-type badge: the colour of its family. Unknown or empty → the neutral chip. */
export function assetTypeBadgeClass(type: string | null | undefined): string {
    return BADGE_CLASS_MAP[(type ?? '').toUpperCase()] ?? BADGE_CLASS_FALLBACK;
}

/** The background class of a subtype badge's dot, the colour of what it contains; `null` for a type with no content. */
export function assetTypeBadgeDotClass(type: string | null | undefined): string | null {
    return BADGE_DOT_CLASS_MAP[(type ?? '').toUpperCase()] ?? null;
}

/**
 * The ETF subtypes, in menu order. The plain `ETF` is **not** here: it is the
 * residual for mixed or unstated content and stays selectable on its own.
 */
export const ETF_SUBTYPES: readonly string[] = ['ETF_STOCK', 'ETF_BOND', 'ETF_COMMODITY', 'ETF_REAL_ESTATE', 'ETF_CRYPTO', 'ETF_MONETARY'];

/** True for the six second-level ETF values, false for `ETF` itself. */
export function isEtfSubtype(type: string | null | undefined): boolean {
    return ETF_SUBTYPES.includes((type ?? '').toUpperCase());
}

/**
 * Roll-up map for {@link primaryAssetType}. Only the entries that actually move
 * are listed; everything else resolves to itself.
 *
 * `ETF_MONETARY` is absent **on purpose** — see {@link primaryAssetType}.
 */
const PRIMARY_TYPE_MAP: Record<string, string> = {
    ETF_STOCK: 'STOCK',
    ETF_BOND: 'BOND',
    ETF_COMMODITY: 'COMMODITY',
    ETF_REAL_ESTATE: 'REAL_ESTATE',
    ETF_CRYPTO: 'CRYPTO',
    CROWDFUND_REAL_ESTATE: 'REAL_ESTATE',
};

/**
 * Resolve an asset type to the type that describes **what it contains**.
 *
 * `ETF_STOCK` → `STOCK`, because the question this answers is "am I as diversified
 * as I think I am?", and to that question the wrapper says nothing: an equity ETF
 * and a share are both equity exposure. Use this wherever types are *aggregated* —
 * allocation rings, concentration, breakdowns. Do **not** use it where a single
 * asset is *shown*: there the badge must keep saying `ETF_STOCK`, because that is
 * the instrument the user actually owns.
 *
 * ## Never derive this by splitting the string
 *
 * `'REAL_ESTATE'.split('_')[0]` is `'REAL'`, which is not an asset type and never
 * was. `REAL_ESTATE` and `ETF_REAL_ESTATE` are a primary type and a subtype that
 * both contain an underscore, so the separator carries no meaning. The map above
 * is the only correct source, and it is explicit for exactly this reason.
 *
 * ## The codomain is smaller than the enum, but it is not the base types
 *
 * The 18 `AssetType` values collapse onto **12**: the 11 non-subtype values, plus
 * `ETF_MONETARY`, which returns *itself*. A money-market fund has no base type to
 * roll up to — cash is an account balance, not an asset that gets bought — and the
 * two candidates are both wrong: `ETF` would bury it among mixed funds, and
 * `LIQUIDITY` is not an `AssetType` at all (the backend injects cash into that
 * bucket separately, so borrowing the name would double-count it).
 *
 * A consumer must therefore treat the result as "an asset type", not as "a base
 * type", and must not assume the result is free of ETF values.
 *
 * ## Unknown input returns itself, not OTHER
 *
 * A value this map has never heard of is its own primary type. Silently rewriting
 * it to `OTHER` would hide a new enum value inside the one bucket nobody inspects;
 * returning it unchanged keeps it visible and lets the enum gate test do the
 * complaining. Only `null`/`undefined`/empty fall back to `OTHER`.
 *
 * @example primaryAssetType('ETF_STOCK')      // 'STOCK'
 * @example primaryAssetType('ETF_REAL_ESTATE')// 'REAL_ESTATE'
 * @example primaryAssetType('CROWDFUND_REAL_ESTATE') // 'REAL_ESTATE'
 * @example primaryAssetType('ETF_MONETARY')   // 'ETF_MONETARY'  ← itself
 * @example primaryAssetType('ETF')            // 'ETF'           ← the residual stays
 * @example primaryAssetType(null)             // 'OTHER'
 */
export function primaryAssetType(type: string | null | undefined): string {
    const raw = (type ?? '').trim().toUpperCase();
    if (raw === '') return 'OTHER';
    return PRIMARY_TYPE_MAP[raw] ?? raw;
}

/**
 * Get the icon URL for an asset type.
 * Falls back to 'other.png' for unknown types.
 */
export function getAssetTypeIconUrl(type: string | null | undefined): string {
    const filename = PNG_MAP[(type ?? '').toUpperCase()] ?? 'other';
    return `/icons/asset-types/${filename}.png`;
}

/**
 * Resolve an asset type to the **family** it belongs to: `ETF_STOCK` → `ETF`.
 *
 * The container view, the counterpart of {@link primaryAssetType} (the content view). Types that
 * specialise nothing are their own family, the generic members included (`ETF` → `ETF`). Input
 * rules match `primaryAssetType`: case and surrounding spaces are ignored, an unknown value
 * returns itself, and only `null`/`undefined`/empty fall back to `OTHER`.
 *
 * @example assetTypeFamily('ETF_STOCK')  // 'ETF'
 * @example assetTypeFamily('ETF')        // 'ETF'
 * @example assetTypeFamily('STOCK')      // 'STOCK'
 */
export function assetTypeFamily(type: string | null | undefined): string {
    const raw = (type ?? '').trim().toUpperCase();
    if (raw === '') return 'OTHER';
    return ASSET_TYPE_FAMILY[raw] ?? raw;
}

/**
 * True when a proposed type only names the **family** of the current one: `ETF` against a stored
 * `ETF_STOCK`. A provider that cannot tell the content — Borsa Italiana says `ETF` for all of
 * ETFplus — agrees with the subtype rather than contradicting it: the developer's rule (K step 17,
 * item 17) is that a parent-type suggestion counts as valid. Equal values, a refinement (`ETF` →
 * `ETF_STOCK`), sibling subtypes, different families and blank input all return false. Case and
 * surrounding spaces are ignored, as in {@link assetTypeFamily}.
 *
 * @example isFamilyOnlyProposal('ETF_STOCK', 'ETF')  // true
 * @example isFamilyOnlyProposal('ETF', 'ETF_STOCK')  // false — a refinement is still offered
 */
export function isFamilyOnlyProposal(current: string | null | undefined, proposed: string | null | undefined): boolean {
    const stored = (current ?? '').trim().toUpperCase();
    const offered = (proposed ?? '').trim().toUpperCase();
    if (stored === '' || offered === '' || stored === offered) return false;
    return assetTypeFamily(stored) === offered;
}

/**
 * Screen order of the asset type menu, and the single place that decides it.
 *
 * ⚠️ Hand-written on purpose, and it must stay that way. `ASSET_TYPES` is derived from
 * the generated Zod schema, so mapping over it was complete *by construction*: every
 * enum value reached the menu whether anyone remembered it or not. Ordering by hand to
 * group the families buys that ordering at the price of completeness — a type added
 * tomorrow would simply fail to appear in the creation dialog, in silence.
 *
 * The price is paid back by `assetTypeTables.test.ts`, which reads this array and the
 * backend enum and asserts they hold the same values. It reads the array **textually**
 * rather than importing it, because `generated.ts` is gitignored: on a checkout where
 * `api sync` has not run, an importing test would compare an empty list to an empty
 * list and report success.
 *
 * The order is the enum's own, with each family kept together where its container sits:
 * the generic member first, then what it may contain. A family must stay contiguous —
 * {@link buildAssetTypeTree} gathers every member under its container wherever it is
 * listed, so a scattered family would make the screen stop following this array, which
 * is then no longer the single place that decides the order. The gate asserts that too.
 */
export const ASSET_TYPE_MENU_ORDER: readonly string[] = [
    'STOCK',
    // ── ETF family: the generic wrapper first, then what it may wrap ──
    'ETF',
    'ETF_STOCK',
    'ETF_BOND',
    'ETF_COMMODITY',
    'ETF_REAL_ESTATE',
    'ETF_CRYPTO',
    'ETF_MONETARY',
    'BOND',
    'CRYPTO',
    'FUND',
    // ── Crowdfunding family ──
    'CROWDFUND',
    'CROWDFUND_REAL_ESTATE',
    'HOLD',
    'COMMODITY',
    'REAL_ESTATE',
    'INDEX',
    'OTHER',
];

/** A row of the asset type select. */
export interface AssetTypeTreeItem extends TreeSelectItem {
    label: string;
    icon: string;
    /** What the generic member of a family stands for — "mixed or unstated content" under ETF. */
    hint?: string;
    /** The family the row sits in; rows at the root have none. */
    family?: string;
}

/** True for a type that others specialise — a family container such as `ETF`. */
function isFamilyContainer(type: string): boolean {
    return Object.values(ASSET_TYPE_FAMILY).includes(type);
}

/**
 * Build the two-level tree of the asset type select (R15, decision D-K1).
 *
 * The types that specialise nothing sit at the root, in inline groups; each family becomes a
 * group that opens and closes like the indicator families of the signals panel, headed by its
 * container. The generic member stays an ordinary, selectable row — the first of its group, with
 * a hint saying what "generic" means there — because groups are never selectable: the group row
 * `ETF` opens the family, the row `ETF` inside it *is* the choice "an ETF of mixed or unstated
 * content". That is the argument B made for plain section titles, and the tree keeps it.
 *
 * `searchText` holds the enum value, the label and the hint, lower-cased as `TreeSelect` expects:
 * the value lets a code-minded user type `etf_bond`, the label is what everybody else reads.
 */
export function buildAssetTypeTree(t: (key: string) => string): TreeSelectGroup<AssetTypeTreeItem>[] {
    const groups: TreeSelectGroup<AssetTypeTreeItem>[] = [];
    let rootRun: AssetTypeTreeItem[] = [];

    const row = (type: string, family?: string): AssetTypeTreeItem => {
        const label = t(`assets.types.${type}`) || type;
        const hint = family === type ? t(`assets.typeHints.${type}`) : undefined;
        return {value: type, label, icon: getAssetTypeIconUrl(type), hint, family, searchText: [type, label, hint ?? ''].join(' ').toLocaleLowerCase()};
    };
    const closeRootRun = () => {
        if (rootRun.length === 0) return;
        groups.push({key: `__root-${groups.length}`, label: '', subtitle: '', items: rootRun, inline: true});
        rootRun = [];
    };

    for (const type of ASSET_TYPE_MENU_ORDER) {
        if (type in ASSET_TYPE_FAMILY) continue; // listed under its container
        if (!isFamilyContainer(type)) {
            rootRun.push(row(type));
            continue;
        }
        closeRootRun();
        const members = [type, ...ASSET_TYPE_MENU_ORDER.filter((candidate) => ASSET_TYPE_FAMILY[candidate] === type)];
        groups.push({key: type, label: t(`assets.typeSections.${type}`) || type, subtitle: '', icon: getAssetTypeIconUrl(type), items: members.map((member) => row(member, type))});
    }
    closeRootRun();
    return groups;
}

// =============================================================================
// IDENTIFIER TYPES — derived from backend enum via Zod schema
// =============================================================================

export const IDENTIFIER_TYPES = schemas.IdentifierType.options;

/**
 * Map IdentifierType enum value to a human-readable label.
 * Upper-case acronyms stay as-is; multi-word → Title Case.
 */
function identifierLabel(type: string): string {
    const ACRONYMS = new Set(['ISIN', 'CUSIP', 'SEDOL', 'FIGI', 'UUID']);
    if (ACRONYMS.has(type)) return type;
    return type.charAt(0) + type.slice(1).toLowerCase(); // TICKER → Ticker, OTHER → Other
}

/**
 * Build a list of [label, value] pairs for non-empty identifiers on an asset.
 * Derives field names from the IdentifierType enum to stay in sync with backend.
 *
 * @example buildIdentifiersList(asset) → [['ISIN', 'IE00B4L5Y983'], ['Ticker', 'VWCE']]
 */
export function buildIdentifiersList(asset: Record<string, unknown>): [string, string][] {
    return IDENTIFIER_TYPES.flatMap((type): [string, string][] => {
        const label = identifierLabel(type);
        const raw = asset[`identifier_${type.toLowerCase()}`];
        // identifier_other is a JSON list → expand into one [label, value] entry per soft identifier
        const values = Array.isArray(raw) ? raw : [raw];
        return values.filter((v): v is string => typeof v === 'string' && v.length > 0).map((v): [string, string] => [label, v]);
    });
}

// =============================================================================
// SECTOR KEYS — loaded from backend via GET /utilities/sectors
// =============================================================================

import {getSectorKeys} from '$lib/stores/reference/sectorStore';

/**
 * Static fallback used before sectorStore is loaded.
 * Matches the backend FinancialSector enum — kept in sync manually
 * as a safety net for the brief window before the API call completes.
 */
const SECTOR_KEYS_FALLBACK: readonly string[] = ['Industrials', 'Technology', 'Financials', 'Consumer Discretionary', 'Health Care', 'Real Estate', 'Basic Materials', 'Energy', 'Consumer Staples', 'Telecommunication', 'Utilities', 'Corporate Bonds', 'Government Bonds', 'Other'];

/**
 * Get the standard financial sector keys.
 *
 * Returns data from the sectorStore (loaded from backend API) when available,
 * otherwise falls back to a static list. Components using sector selects
 * should call `ensureSectorsLoaded()` early to populate the store.
 */
export function getSectorKeysList(): readonly string[] {
    const keys = getSectorKeys();
    return keys.length > 0 ? keys : SECTOR_KEYS_FALLBACK;
}

/**
 * Convert a backend sector key (e.g. "Consumer Discretionary") to
 * the corresponding i18n key (e.g. "ConsumerDiscretionary").
 *
 * Convention: strip spaces → PascalCase.
 * Single-word keys like "Technology" pass through unchanged.
 */
export function sectorI18nKey(backendKey: string): string {
    return backendKey.replaceAll(' ', '');
}
