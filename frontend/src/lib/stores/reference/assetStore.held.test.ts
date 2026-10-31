/**
 * assetStore — `held_by_me` / `held_by_others` through normalize (Y2 FB-10).
 *
 * The asset picker groups its list like the Assets page — yours, other users', watched — by what the asset list says is held now.
 * The panels read those two flags from this store, so `normalize()` has to copy them: a normalizer that forgets them puts every
 * asset in «watched», silently.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({zodiosApi: {list_assets_api_v1_assets_query_get: vi.fn(async () => [])}}));

import {getAssetInfo, mergeAssets, resetAssetStore} from './assetStore';

describe('assetStore — held_by_me and held_by_others', () => {
    beforeEach(() => {
        resetAssetStore();
        mergeAssets([
            {id: 9201, display_name: 'Mine', currency: 'EUR', held_by_me: true, held_by_others: false},
            {id: 9202, display_name: 'Theirs', currency: 'EUR', held_by_me: false, held_by_others: true},
            {id: 9203, display_name: 'No flags in the payload', currency: 'EUR'},
        ]);
    });

    it('keeps the flags an API item carries', () => {
        expect(getAssetInfo(9201)).toMatchObject({held_by_me: true, held_by_others: false});
        expect(getAssetInfo(9202)).toMatchObject({held_by_me: false, held_by_others: true});
    });

    it('leaves them absent when the payload has none (the picker then leaves the asset ungrouped)', () => {
        expect(getAssetInfo(9203)?.held_by_me).toBeUndefined();
        expect(getAssetInfo(9203)?.held_by_others).toBeUndefined();
    });

    it('a partial PATCH of another field keeps the cached flags', () => {
        mergeAssets([{id: 9201, display_name: 'Mine renamed'}]);
        expect(getAssetInfo(9201)).toMatchObject({display_name: 'Mine renamed', held_by_me: true});
    });
});
