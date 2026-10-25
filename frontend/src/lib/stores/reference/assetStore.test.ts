/**
 * assetStore — `quote_base_quantity` through normalize and merge (W5-9).
 *
 * The transaction form calculates «Total amount / Unit price» from the asset's quote base (100 for a bond quoted per 100
 * nominal), read from this store. So the field has to survive the store's own ingress: `normalize()` must copy it (a
 * normalizer that forgets it turns every bond into base 1, silently), a partial PATCH must keep the cached one, and a
 * PATCH that carries a new value must replace it.
 *
 * No DOM: node env. `$lib/api` is mocked because the store module imports it for the loader — never called here.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({zodiosApi: {list_assets_api_v1_assets_query_get: vi.fn(async () => [])}}));

import {getAssetInfo, mergeAssets, resetAssetStore} from './assetStore';

const BOND = 9101;
const STOCK = 9102;
const LEGACY = 9103;

describe('assetStore — quote_base_quantity', () => {
    beforeEach(() => {
        resetAssetStore();
        mergeAssets([
            {id: BOND, display_name: 'Bond', currency: 'EUR', asset_type: 'BOND', quote_base_quantity: 100, active: true},
            {id: STOCK, display_name: 'Stock', currency: 'EUR', quote_base_quantity: 1, active: true},
            {id: LEGACY, display_name: 'No base in the payload', currency: 'EUR', active: true},
        ]);
    });

    it('normalize keeps the value an API item carries', () => {
        expect(getAssetInfo(BOND)?.quote_base_quantity).toBe(100);
        expect(getAssetInfo(STOCK)?.quote_base_quantity).toBe(1);
    });

    it('a payload without the field leaves it absent (the form reads that as 1), not a made-up number', () => {
        expect(getAssetInfo(LEGACY)).not.toBeNull();
        expect(getAssetInfo(LEGACY)?.quote_base_quantity).toBeUndefined();
    });

    it('a union-wrapped value from the generated client ([100]) is flattened, and null stays null', () => {
        mergeAssets([
            {id: 9104, display_name: 'Wrapped', currency: 'EUR', quote_base_quantity: [100]},
            {id: 9105, display_name: 'Null', currency: 'EUR', quote_base_quantity: null},
        ]);
        expect(getAssetInfo(9104)?.quote_base_quantity).toBe(100);
        expect(getAssetInfo(9105)?.quote_base_quantity).toBeNull();
    });

    it('a partial PATCH of another field keeps the cached quote base', () => {
        mergeAssets([{id: BOND, display_name: 'Bond renamed'}]);
        const bond = getAssetInfo(BOND);
        expect(bond?.display_name).toBe('Bond renamed');
        expect(bond?.quote_base_quantity).toBe(100);
        expect(bond?.asset_type).toBe('BOND');
    });

    it('a PATCH that carries a new quote base replaces it, and the rest of the row stays', () => {
        mergeAssets([{id: BOND, quote_base_quantity: 1000}]);
        const bond = getAssetInfo(BOND);
        expect(bond?.quote_base_quantity).toBe(1000);
        expect(bond?.display_name).toBe('Bond');
        expect(bond?.currency).toBe('EUR');
    });

    it('a PATCH that sets the base to null clears it (the form then reads 1)', () => {
        mergeAssets([{id: BOND, quote_base_quantity: null}]);
        expect(getAssetInfo(BOND)?.quote_base_quantity).toBeNull();
    });
});
