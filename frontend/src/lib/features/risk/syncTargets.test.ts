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
 * sync, the rest navigate. The last block pins it, one case per row of the rule;
 * written red first, against a module that does not export it.
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
 * them — and `navigate_asset`, `navigate_fx` and `add_fx_pair`, which leave for the asset, the pair
 * or the FX page. A navigation that needs a target and has none goes nowhere, and so does an action
 * the rule does not know: `null`, never a guess.
 *
 * Pure, so it is pinned here, one case per row, on the exact object each row returns.
 */

/** What the panel does with an action, as decision B names it: declared here, so the cases compile before the export exists. */
type LabQualityAction = {kind: 'sync'} | {kind: 'navigate'; href: string};

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

    it('sends add_fx_pair to the FX page, whatever the target: a pair with no route has no page of its own yet', () => {
        expect(labQualityAction('add_fx_pair', null)).toEqual({kind: 'navigate', href: '/fx'});
        expect(labQualityAction('add_fx_pair', 'EUR-USD'), 'a target does not move add_fx_pair off the FX page').toEqual({kind: 'navigate', href: '/fx'});
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
