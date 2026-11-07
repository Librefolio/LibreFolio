/**
 * P1 (lot P9): an INDEX is not something a plan can buy, so «Your Assets» and the search leave it out. Only those two lists:
 * the type of a manual Asset is the user's own word. The search's half lives in `AssetsStep` (a filter over the asset cache
 * with `isIndexAssetClass`); this pins the rule itself and the list of the user's own positions.
 */
import {describe, expect, it} from 'vitest';
import {isIndexAssetClass, ownedAssets} from './copies';
import type {PlannerSource, SourceAsset} from './source';

function asset(id: number, assetClass: string): SourceAsset {
    return {asset_id: `asset-${id}`, source_asset_id: id, name: `Asset ${id}`, ticker: null, asset_class: assetClass, icon_url: null, active: true, provenance_id: 'p'};
}

function source(assets: SourceAsset[]): PlannerSource {
    return {
        asOf: '2026-11-07',
        targetCurrency: 'EUR',
        generatedAt: '2026-11-07T10:00:00Z',
        provenance: [],
        assets,
        brokers: [{broker_id: 'broker-1', source_broker_id: 1, name: 'B', icon_url: null, access_role: 'OWNER', ownership_share: '1', observed_currencies: [], active: true, execution_profile_status: 'ok', provenance_id: 'p'}],
        holdings: assets.map((row) => ({holding_id: `h-${row.source_asset_id}`, asset_id: row.asset_id, broker_id: 'broker-1', provenance_id: 'p'})),
        cash: [],
        prices: [],
        classifications: [],
        fxQuotes: [],
        currentDistribution: null,
        issues: [],
    };
}

describe('isIndexAssetClass', () => {
    it('is true only for INDEX', () => {
        expect(isIndexAssetClass('INDEX')).toBe(true);
        for (const other of ['ETF', 'STOCK', 'BOND', 'OTHER', 'index', '', null, undefined]) expect(isIndexAssetClass(other)).toBe(false);
    });
});

describe('ownedAssets', () => {
    it('lists the held Assets without the indices, and counts no index as an unmatched position', () => {
        const owned = ownedAssets(source([asset(1, 'ETF'), asset(2, 'INDEX'), asset(3, 'STOCK')]));
        expect(owned.rows.map((row) => row.asset.source_asset_id).sort()).toEqual([1, 3]);
        expect(owned.unresolved).toBe(0);
    });

    it('keeps an Asset of any other type', () => {
        const owned = ownedAssets(source([asset(4, 'ETF_STOCK'), asset(5, 'OTHER')]));
        expect(owned.rows).toHaveLength(2);
    });
});
