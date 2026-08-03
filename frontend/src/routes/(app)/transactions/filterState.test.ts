import {describe, expect, it} from 'vitest';

import {applyTransactionColumnFilters, buildTransactionsFiltersUrl, parseTransactionFilters, toTransactionColumnFilters} from './filterState';

describe('transaction without-asset filter', () => {
    const withoutAssetColumnFilter = {
        asset_id: {type: 'enum' as const, selected: ['__null__']},
    };

    it('stores the null sentinel without creating NaN', () => {
        const result = applyTransactionColumnFilters({}, withoutAssetColumnFilter);

        expect(result).not.toBeNull();
        expect(result?.without_asset).toBe(true);
        expect(result?.asset_id).toBeUndefined();
        expect(result?.asset_ids).toBeUndefined();
    });

    it('returns null when the same null filter is emitted again', () => {
        const first = applyTransactionColumnFilters({}, withoutAssetColumnFilter);
        expect(first).not.toBeNull();

        expect(applyTransactionColumnFilters(first!, withoutAssetColumnFilter)).toBeNull();
    });

    it('keeps null and numeric asset selections distinct', () => {
        const result = applyTransactionColumnFilters(
            {},
            {
                asset_id: {type: 'enum', selected: ['__null__', '5']},
            },
        );

        expect(result?.without_asset).toBe(true);
        expect(result?.asset_id).toBeUndefined();
        expect(result?.asset_ids).toEqual([5]);
    });

    it('restores the null sentinel in DataTable column filters', () => {
        expect(toTransactionColumnFilters({without_asset: true})).toEqual({
            asset_id: {type: 'enum', selected: ['__null__']},
        });
        expect(toTransactionColumnFilters({without_asset: true, asset_id: 42}).asset_id).toEqual({
            type: 'enum',
            selected: ['__null__', '42'],
        });
    });

    it('round-trips through the URL without asset_id=NaN', () => {
        const url = buildTransactionsFiltersUrl({without_asset: true});
        const query = new URL(url, 'http://localhost').searchParams;
        const parsed = parseTransactionFilters(query);

        expect(url).toBe('/transactions?without_asset=true');
        expect(url).not.toContain('NaN');
        expect(parsed.without_asset).toBe(true);
        expect(parsed.asset_id).toBeUndefined();
    });

    it('drops legacy malformed asset_id=NaN values', () => {
        const parsed = parseTransactionFilters(new URLSearchParams('asset_id=NaN'));

        expect(parsed.asset_id).toBeUndefined();
        expect(parsed.without_asset).toBeUndefined();
    });
});
