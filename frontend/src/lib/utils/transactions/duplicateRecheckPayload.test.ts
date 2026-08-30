import {describe, it, expect} from 'vitest';
import {buildDuplicateRecheckPayload} from './duplicateRecheckPayload';
import {FAKE_ASSET_ID_BASE} from '$lib/utils/brim/isFakeAssetId';

interface Tx {
    asset_id?: number | null;
    type?: string | null;
    date?: string;
}

const FAKE = FAKE_ASSET_ID_BASE; // placeholder ids sit just below 2^31

const required = new Set(['BUY', 'SELL', 'DIVIDEND', 'ADJUSTMENT']);
const assetFieldOf = (type: string) => (required.has(type) ? 'required' : 'optional');

const row = (index: number, tx: Tx) => ({index, tx});

describe('buildDuplicateRecheckPayload', () => {
    it('substitutes a resolved fake id with the real instrument', () => {
        const asked = buildDuplicateRecheckPayload([row(0, {asset_id: FAKE, type: 'BUY'})], new Map([[FAKE, 42]]), assetFieldOf);

        expect(asked).toHaveLength(1);
        expect(asked[0].clone.asset_id).toBe(42);
        expect(asked[0].row.index).toBe(0);
    });

    it('does not mutate the row it was given', () => {
        const original: Tx = {asset_id: FAKE, type: 'BUY'};
        buildDuplicateRecheckPayload([row(0, original)], new Map([[FAKE, 42]]), assetFieldOf);

        expect(original.asset_id).toBe(FAKE);
    });

    it('drops a row whose type requires an instrument that is still unresolved', () => {
        // The 422 this avoids used to fail the whole re-check, and the wizard fell back
        // silently on the verdict computed before the user's corrections.
        const asked = buildDuplicateRecheckPayload([row(0, {asset_id: FAKE, type: 'BUY'})], new Map(), assetFieldOf);

        expect(asked).toEqual([]);
    });

    it('keeps a row whose type does not require an instrument', () => {
        const asked = buildDuplicateRecheckPayload([row(0, {asset_id: null, type: 'DEPOSIT'}), row(1, {type: 'FEE'})], new Map(), assetFieldOf);

        expect(asked.map((a) => a.row.index)).toEqual([0, 1]);
    });

    it('keeps an asset-less row that has no type at all (empty type → not required)', () => {
        // asset_id null and no type: String(undefined ?? '') feeds assetFieldOf('') → optional.
        const asked = buildDuplicateRecheckPayload([row(0, {asset_id: null})], new Map(), assetFieldOf);

        expect(asked.map((a) => a.row.index)).toEqual([0]);
    });

    it('keeps a real instrument id untouched', () => {
        const asked = buildDuplicateRecheckPayload([row(7, {asset_id: 91, type: 'SELL'})], new Map([[FAKE, 42]]), assetFieldOf);

        expect(asked[0].clone.asset_id).toBe(91);
    });

    it('renumbers nothing: the caller maps verdicts back through the paired row', () => {
        // The endpoint answers by position in the *submitted* list. Dropping row 1 must
        // therefore not make row 2's verdict land on row 1.
        const asked = buildDuplicateRecheckPayload([row(10, {asset_id: null, type: 'DEPOSIT'}), row(11, {asset_id: FAKE, type: 'BUY'}), row(12, {asset_id: 5, type: 'SELL'})], new Map(), assetFieldOf);

        expect(asked.map((a) => a.row.index)).toEqual([10, 12]);
    });

    it('returns an empty list when every row is unresolved, so no call is made', () => {
        const asked = buildDuplicateRecheckPayload([row(0, {asset_id: FAKE, type: 'BUY'}), row(1, {asset_id: FAKE - 1, type: 'ADJUSTMENT'})], new Map(), assetFieldOf);

        expect(asked).toEqual([]);
    });

    it('treats an unknown type as not requiring an instrument, rather than dropping the row', () => {
        const asked = buildDuplicateRecheckPayload([row(0, {asset_id: null, type: 'SOMETHING_NEW'})], new Map(), assetFieldOf);

        expect(asked).toHaveLength(1);
    });
});
