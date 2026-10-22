/**
 * @vitest-environment node
 *
 * syncTargets — pure unit tests (node env, no jsdom).
 *
 * `buildSyncTargets` is the rule behind a risk page's "sync" button: the prices of
 * the assets an answer rests on, plus — for every one of them quoted in a currency
 * other than the answer's — the exchange rate that converts it. R2-128 is what the
 * rule looks like half-applied: a page that refreshes the prices and leaves a
 * converted series standing on stale rates. So it is pinned here, where the lookup
 * and the configured pairs are plain arguments, instead of through a page whose
 * seed decides which of its branches ever run.
 *
 * `labQualityAction` is this module's other rule (decision B, the developer, 05/10/2026):
 * what an action of the lab's data-quality banner does — a sync opens the lab's own
 * sync, adding a pair opens the add-pair dialog (Q-TC23-1), the rest navigate. The
 * last two blocks pin it and the dialog's two sides (`addPairSides`), one case per
 * row of the rule; written red first, against a module that does not export them.
 */
import {describe, expect, it} from 'vitest';

import * as syncTargets from './syncTargets';
import {buildSyncTargets, type SyncAssetInfo} from './syncTargets';

/** The fields `SyncAssetInfo` documents, and the only ones the output may carry. */
const DOCUMENTED_FIELDS = ['asset_type', 'currency', 'display_name', 'icon_url', 'id', 'provider_code'];

/** An asset carrying every documented field; overrides replace any of them. */
function info(id: number, currency: string, overrides: Partial<SyncAssetInfo> = {}): SyncAssetInfo {
    return {id, display_name: `Asset ${id}`, currency, icon_url: null, asset_type: 'STOCK', provider_code: 'yfinance', ...overrides};
}

/** A lookup over a fixed catalogue: anything else is unknown, as `getAssetInfo` answers it. */
function lookupOf(...assets: SyncAssetInfo[]): (assetId: number) => SyncAssetInfo | undefined {
    const byId = new Map(assets.map((asset) => [asset.id, asset]));
    return (assetId) => byId.get(assetId);
}

const NO_CONFIGURED_PAIRS: ReadonlySet<string> = new Set();

describe('buildSyncTargets — the assets', () => {
    it('deduplicates, orders by id and skips the ids the lookup does not know', () => {
        const lookup = lookupOf(info(1, 'EUR'), info(3, 'EUR'), info(5, 'EUR'));
        const {assets} = buildSyncTargets([5, 3, 5, 99, 1, 3], 'EUR', lookup, NO_CONFIGURED_PAIRS);
        expect(assets.map((asset) => asset.id)).toEqual([1, 3, 5]);
    });

    it('skips a null answer from the lookup exactly like an unknown id', () => {
        const {assets} = buildSyncTargets([1, 2], 'EUR', (assetId) => (assetId === 1 ? info(1, 'EUR') : null), NO_CONFIGURED_PAIRS);
        expect(assets.map((asset) => asset.id)).toEqual([1]);
    });

    it('has nothing to sync for an empty selection', () => {
        expect(buildSyncTargets([], 'EUR', lookupOf(info(1, 'USD')), new Set(['EUR-USD']))).toEqual({assets: [], fxPairs: []});
    });

    it('carries exactly the documented fields, whatever else the lookup holds', () => {
        // The store's entries carry far more than the modal reads — activity,
        // usage counters, identifiers — and none of it may ride along.
        const rich = {...info(7, 'USD', {icon_url: 'https://example.test/7.png', asset_type: 'ETF', provider_code: 'justetf'}), active: true, tx_count_own: 4, identifier_isin: 'IE00B4L5Y983'};
        const [asset] = buildSyncTargets([7], 'EUR', () => rich, NO_CONFIGURED_PAIRS).assets;
        expect(Object.keys(asset).sort()).toEqual(DOCUMENTED_FIELDS);
        expect(asset).toEqual({id: 7, display_name: 'Asset 7', currency: 'USD', icon_url: 'https://example.test/7.png', asset_type: 'ETF', provider_code: 'justetf'});

        // And nothing is invented for an entry that carries only the required three.
        const bare: SyncAssetInfo = {id: 8, display_name: 'Bare', currency: 'EUR'};
        const [minimal] = buildSyncTargets([8], 'EUR', () => bare, NO_CONFIGURED_PAIRS).assets;
        expect(Object.keys(minimal).every((field) => DOCUMENTED_FIELDS.includes(field))).toBe(true);
        expect(minimal).toEqual({id: 8, display_name: 'Bare', currency: 'EUR'});
    });
});

describe('buildSyncTargets — the exchange-rate pairs', () => {
    it('proposes the pair of an asset quoted outside the target currency when it is configured', () => {
        expect(buildSyncTargets([1], 'EUR', lookupOf(info(1, 'USD')), new Set(['EUR-USD'])).fxPairs).toEqual(['EUR-USD']);
    });

    it('never proposes a pair that is not configured: there would be no route to fetch it', () => {
        const lookup = lookupOf(info(1, 'USD'), info(2, 'GBP'));
        expect(buildSyncTargets([1, 2], 'EUR', lookup, NO_CONFIGURED_PAIRS).fxPairs).toEqual([]);
        // Control: the same selection with one route configured gets exactly that
        // one, so the empty list above is the guard and not a rule that never fires.
        expect(buildSyncTargets([1, 2], 'EUR', lookup, new Set(['EUR-USD'])).fxPairs).toEqual(['EUR-USD']);
    });

    it('names the pair by its sorted slug, whichever side the target currency is on', () => {
        // Target USD, asset EUR: still `EUR-USD`, never `USD-EUR`…
        expect(buildSyncTargets([1], 'USD', lookupOf(info(1, 'EUR')), new Set(['EUR-USD'])).fxPairs).toEqual(['EUR-USD']);
        // …so a set that spells the pair the other way round configures nothing.
        expect(buildSyncTargets([1], 'USD', lookupOf(info(1, 'EUR')), new Set(['USD-EUR'])).fxPairs).toEqual([]);
    });

    it('deduplicates the pairs and sorts them', () => {
        // Ids ascend while the slugs they produce descend (EUR-USD, EUR-GBP,
        // CHF-EUR), so an unsorted list would come back in the wrong order; two
        // USD assets make the duplicate.
        const lookup = lookupOf(info(1, 'USD'), info(2, 'USD'), info(3, 'GBP'), info(4, 'CHF'));
        const configured = new Set(['EUR-USD', 'EUR-GBP', 'CHF-EUR']);
        expect(buildSyncTargets([1, 2, 3, 4], 'EUR', lookup, configured).fxPairs).toEqual(['CHF-EUR', 'EUR-GBP', 'EUR-USD']);
    });

    it('proposes no pair when every asset is already quoted in the target currency', () => {
        const lookup = lookupOf(info(1, 'EUR'), info(2, 'EUR'));
        const everything = new Set(['EUR-USD', 'EUR-GBP', 'CHF-EUR']);
        const {assets, fxPairs} = buildSyncTargets([1, 2], 'EUR', lookup, everything);
        expect(fxPairs).toEqual([]);
        // Control: the prices still need syncing — no pair does not mean no target.
        expect(assets.map((asset) => asset.id)).toEqual([1, 2]);
    });

    it('proposes no pair for an id the lookup does not know', () => {
        // Unknown means no currency to convert from, whatever is configured.
        expect(buildSyncTargets([99], 'EUR', lookupOf(info(1, 'USD')), new Set(['EUR-USD']))).toEqual({assets: [], fxPairs: []});
    });
});

/**
 * ─── labQualityAction: what an action of the lab's data-quality banner does ────────────────────
 *
 * The lab draws one `DataQualityBanner` above its one notice (decision B), over the issues every
 * section's controllers hold. The banner only reports what was pressed — `onaction(action, target)` —
 * and its host decides. For an asset set the backend sends five actions (D373,
 * `service.py::_data_quality_issues`): `sync_asset_prices` and `sync_fx_pair`, which the lab answers
 * with its own sync — the page's one, scoped to the selection, prices and the rates that convert
 * them — and `navigate_asset` and `navigate_fx`, which leave for the asset or the pair, and
 * `add_fx_pair`, which stays on the page: the panel opens the add-pair dialog itself, on the pair
 * that was pressed, or empty when the issue names none (Q-TC23-1; the FX page used to be the
 * answer). A navigation that needs a target and has none goes nowhere, and so does an action
 * the rule does not know: `null`, never a guess.
 *
 * Pure, so it is pinned here, one case per row, on the exact object each row returns.
 */

/** What the panel does with an action, as decision B and Q-TC23-1 name it: declared here, so the cases compile before the export exists. */
type LabQualityAction = {kind: 'sync'} | {kind: 'navigate'; href: string} | {kind: 'add_pair'; pair: string};

/**
 * `labQualityAction`, called through the module. Until the export exists every case below fails
 * here, on the assertion that names what is missing, rather than on a `TypeError` thrown before any
 * assertion ran.
 */
function labQualityAction(action: string, target: string | null): LabQualityAction | null {
    const rule = (syncTargets as unknown as Record<string, unknown>).labQualityAction;
    expect(typeof rule, 'syncTargets exports no labQualityAction(): the lab banner has no rule turning its actions into a sync or a navigation').toBe('function');
    return (rule as (action: string, target: string | null) => LabQualityAction | null)(action, target);
}

describe('labQualityAction — what an action of the lab banner does', () => {
    it("opens the lab's own sync for both sync actions, whatever their target", () => {
        expect(labQualityAction('sync_asset_prices', '12')).toEqual({kind: 'sync'});
        expect(labQualityAction('sync_asset_prices', null)).toEqual({kind: 'sync'});
        expect(labQualityAction('sync_fx_pair', 'EUR-USD')).toEqual({kind: 'sync'});
        expect(labQualityAction('sync_fx_pair', null)).toEqual({kind: 'sync'});
        // The rule is the prefix, not a list of two: a sync the backend adds later opens the same sync.
        expect(labQualityAction('sync_invented_series', null), 'an action starting with sync_ is a sync').toEqual({kind: 'sync'});
    });

    it('opens the asset for navigate_asset with a target, and goes nowhere without one', () => {
        expect(labQualityAction('navigate_asset', '12')).toEqual({kind: 'navigate', href: '/assets/12'});
        expect(labQualityAction('navigate_asset', null), 'no target, no asset to open').toBeNull();
    });

    it('opens the pair for navigate_fx with a target, and goes nowhere without one', () => {
        expect(labQualityAction('navigate_fx', 'EUR-USD')).toEqual({kind: 'navigate', href: '/fx/EUR-USD'});
        expect(labQualityAction('navigate_fx', null), 'no target, no pair to open').toBeNull();
    });

    it('opens the add-pair dialog on the pressed pair for add_fx_pair, as written', () => {
        expect(labQualityAction('add_fx_pair', 'EUR-USD'), 'a pair pressed on an add_fx_pair chip is the pair the dialog opens on').toEqual({kind: 'add_pair', pair: 'EUR-USD'});
        // The pair is handed over as it came, not normalised: the dialog's sides are `addPairSides`' business.
        expect(labQualityAction('add_fx_pair', 'chf-eur')).toEqual({kind: 'add_pair', pair: 'chf-eur'});
        // Control: the same pair under navigate_fx still leaves for its page, so the row above is what tells the two apart.
        expect(labQualityAction('navigate_fx', 'EUR-USD')).toEqual({kind: 'navigate', href: '/fx/EUR-USD'});
    });

    it('opens the add-pair dialog empty for add_fx_pair without a pair, and does not leave for the FX page', () => {
        // `MISSING_FX_MARKET` names no cta_target: the dialog is the answer, and it opens with nothing chosen.
        expect(labQualityAction('add_fx_pair', null), 'no pair is an empty dialog, not a navigation and not nothing').toEqual({kind: 'add_pair', pair: ''});
    });

    it('encodes the target as one path segment', () => {
        // A slash in a target must not open a deeper route than the pair's, or the asset's, own.
        expect(labQualityAction('navigate_fx', 'a/b')).toEqual({kind: 'navigate', href: '/fx/a%2Fb'});
        expect(labQualityAction('navigate_asset', 'a/b')).toEqual({kind: 'navigate', href: '/assets/a%2Fb'});
    });

    it('does nothing with an action it does not know, the empty one included', () => {
        expect(labQualityAction('open_invented_panel', '12')).toBeNull();
        expect(labQualityAction('', null)).toBeNull();
        expect(labQualityAction('', '12'), 'an empty action is no action, with a target or without').toBeNull();
        // Mentioning a sync is not starting with one: `RiskPanelHeader`'s looser `includes('sync')` would open it.
        expect(labQualityAction('resync_invented', null), 'only an action starting with sync_ is a sync').toBeNull();
    });
});

/**
 * ─── addPairSides: the sides the add-pair dialog opens on ──────────────────────────────────────
 *
 * The dialog takes a base and a quote, each editable. A pair slug names both only when it is exactly
 * two non-empty parts split on `-`; anything else names no pair the dialog could pre-fill, so it opens
 * empty rather than half-filled. The sides are kept as written: the dialog's own selects know how to
 * read a code, and a case change here would make two spellings of one pair look like two pairs.
 */

/** The two sides the dialog opens on: declared here, so the cases compile before the export exists. */
interface AddPairSides {
    base: string;
    quote: string;
}

/** `addPairSides`, called through the module: until the export exists every case fails on the assertion that names it, not on a `TypeError`. */
function addPairSides(pair: string): AddPairSides {
    const rule = (syncTargets as unknown as Record<string, unknown>).addPairSides;
    expect(typeof rule, 'syncTargets exports no addPairSides(): the add-pair dialog has no rule turning a pair slug into its two sides').toBe('function');
    return (rule as (pair: string) => AddPairSides)(pair);
}

const NO_SIDES: AddPairSides = {base: '', quote: ''};

describe('addPairSides — the sides the add-pair dialog opens on', () => {
    it('gives both sides of a slug of exactly two non-empty parts', () => {
        expect(addPairSides('EUR-USD')).toEqual({base: 'EUR', quote: 'USD'});
        expect(addPairSides('CHF-EUR')).toEqual({base: 'CHF', quote: 'EUR'});
    });

    it('keeps the sides as written, with no case change', () => {
        expect(addPairSides('eur-usd')).toEqual({base: 'eur', quote: 'usd'});
        expect(addPairSides('Eur-uSD')).toEqual({base: 'Eur', quote: 'uSD'});
    });

    it('opens on nothing for the empty slug', () => {
        expect(addPairSides('')).toEqual(NO_SIDES);
    });

    it('opens on nothing for a slug of one part: a lone side is not a pair', () => {
        expect(addPairSides('EUR')).toEqual(NO_SIDES);
    });

    it('opens on nothing for a slug of more than two parts, never on its first two', () => {
        expect(addPairSides('A-B-C')).toEqual(NO_SIDES);
        // An empty part between two sides still makes three parts.
        expect(addPairSides('EUR--USD')).toEqual(NO_SIDES);
    });

    it('opens on nothing when either side is empty', () => {
        expect(addPairSides('-USD')).toEqual(NO_SIDES);
        expect(addPairSides('EUR-')).toEqual(NO_SIDES);
        expect(addPairSides('-')).toEqual(NO_SIDES);
    });
});
