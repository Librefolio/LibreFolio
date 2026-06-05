/**
 * Unit tests for txPayloadHelpers — pure payload building functions.
 */
import {describe, expect, it} from 'vitest';
import {applySignRules, buildSignedCash, fieldEq, buildCreatePayload, buildUpdateDiff, diffDualItem, buildDualCreatePayloads, buildBatchPayload, PATCHABLE_FIELDS} from '../transactions/txPayloadHelpers';
import type {TxFields, TxOriginal, CashValue, ResolvedOp, TxDualSide} from '../transactions/txPayloadHelpers';

// =============================================================================
//  Mock TypeRule factory
// =============================================================================

interface MockRule {
    quantityRule: 'positive' | 'negative' | 'zero';
    cashSign: 'positive' | 'negative' | 'optional';
    cashField: 'required' | 'optional' | 'forbidden';
    assetField: 'required' | 'optional' | 'forbidden';
    requiresPair: boolean;
    eventLinkable?: boolean;
}

function rule(overrides?: Partial<MockRule>): MockRule {
    return {
        quantityRule: 'positive',
        cashSign: 'positive',
        cashField: 'optional',
        assetField: 'optional',
        requiresPair: false,
        eventLinkable: false,
        ...overrides,
    };
}

function cash(code: string, amount: string): CashValue {
    return {code, amount};
}

function baseFields(overrides?: Partial<TxFields>): TxFields {
    return {
        type: 'BUY',
        broker_id: 1,
        date: '2024-06-01',
        quantity: '10',
        asset_id: 42,
        cash: cash('EUR', '100'),
        tags: [],
        description: '',
        cost_basis_override: null,
        ...overrides,
    };
}

function baseOriginal(overrides?: Partial<TxOriginal>): TxOriginal {
    return {
        id: 99,
        type: 'BUY',
        broker_id: 1,
        date: '2024-06-01',
        quantity: '10',
        asset_id: 42,
        cash: cash('EUR', '100'),
        tags: [],
        description: '',
        cost_basis_override: null,
        ...overrides,
    };
}

// =============================================================================
//  applySignRules
// =============================================================================

describe('applySignRules', () => {
    it.each([
        {qty: '10', negQty: false, negCash: false, expectedQty: '10', expectedAmt: '100'},
        {qty: '10', negQty: true, negCash: false, expectedQty: '-10', expectedAmt: '100'},
        {qty: '10', negQty: false, negCash: true, expectedQty: '10', expectedAmt: '-100'},
        {qty: '-10', negQty: true, negCash: true, expectedQty: '-10', expectedAmt: '-100'},
    ])('qty=$qty negQty=$negQty negCash=$negCash → qty=$expectedQty cash=$expectedAmt', ({qty, negQty, negCash, expectedQty, expectedAmt}) => {
        const r = rule({quantityRule: negQty ? 'negative' : 'positive', cashSign: negCash ? 'negative' : 'positive'});
        const {signedQty, signedCash} = applySignRules(qty, cash('EUR', '100'), r as any);
        expect(signedQty).toBe(expectedQty);
        expect(signedCash?.amount).toBe(expectedAmt);
    });

    it('returns null cash when input is null', () => {
        const {signedCash} = applySignRules('5', null, rule() as any);
        expect(signedCash).toBeNull();
    });
});

// =============================================================================
//  buildSignedCash
// =============================================================================

describe('buildSignedCash', () => {
    it('returns null for null input', () => {
        expect(buildSignedCash(null, false)).toBeNull();
        expect(buildSignedCash(null, true)).toBeNull();
        expect(buildSignedCash(undefined, true)).toBeNull();
    });

    it('negates amount when negate=true', () => {
        expect(buildSignedCash(cash('USD', '50'), true)).toEqual({code: 'USD', amount: '-50'});
    });

    it('preserves amount when negate=false', () => {
        expect(buildSignedCash(cash('USD', '50'), false)).toEqual({code: 'USD', amount: '50'});
    });

    it('always takes absolute value before negating', () => {
        expect(buildSignedCash(cash('USD', '-50'), true)).toEqual({code: 'USD', amount: '-50'});
    });
});

// =============================================================================
//  fieldEq
// =============================================================================

describe('fieldEq', () => {
    it.each([
        {key: 'quantity', a: '10', b: '10.000000', expected: true},
        {key: 'quantity', a: '10', b: '11', expected: false},
        {key: 'cash', a: cash('EUR', '1.5'), b: cash('EUR', '1.500'), expected: true},
        {key: 'cash', a: cash('EUR', '1.5'), b: cash('USD', '1.5'), expected: false},
        {key: 'cash', a: null, b: null, expected: true},
        {key: 'cash', a: null, b: cash('EUR', '0'), expected: false},
        {key: 'description', a: '', b: null, expected: true},
        {key: 'description', a: 'hello', b: 'hello', expected: true},
        {key: 'description', a: 'hello', b: 'world', expected: false},
        {key: 'tags', a: ['a', 'b'], b: ['b', 'a'], expected: true},
        {key: 'tags', a: ['a'], b: ['a', 'b'], expected: false},
        {key: 'tags', a: [], b: null, expected: true},
        {key: 'asset_event_id', a: null, b: undefined, expected: true},
        {key: 'asset_event_id', a: 5, b: 5, expected: true},
        {key: 'asset_event_id', a: 5, b: null, expected: false},
    ])('fieldEq($key, $a, $b) → $expected', ({key, a, b, expected}) => {
        expect(fieldEq(key, a, b)).toBe(expected);
    });
});

// =============================================================================
//  buildCreatePayload
// =============================================================================

describe('buildCreatePayload', () => {
    it('includes broker_id, type, date, quantity', () => {
        const p = buildCreatePayload(baseFields(), rule() as any);
        expect(p.broker_id).toBe(1);
        expect(p.type).toBe('BUY');
        expect(p.date).toBe('2024-06-01');
        expect(p.quantity).toBe('10');
    });

    it('includes asset_id when present and not forbidden', () => {
        const p = buildCreatePayload(baseFields({asset_id: 7}), rule() as any);
        expect(p.asset_id).toBe(7);
    });

    it('excludes asset_id when assetField=forbidden', () => {
        const p = buildCreatePayload(baseFields({asset_id: 7}), rule({assetField: 'forbidden'}) as any);
        expect(p.asset_id).toBeUndefined();
    });

    it('includes cash when present and not forbidden', () => {
        const p = buildCreatePayload(baseFields(), rule() as any);
        expect(p.cash).toBeDefined();
    });

    it('excludes cash when cashField=forbidden', () => {
        const p = buildCreatePayload(baseFields(), rule({cashField: 'forbidden'}) as any);
        expect(p.cash).toBeUndefined();
    });

    it('includes tags only when non-empty', () => {
        const p1 = buildCreatePayload(baseFields({tags: ['hello']}), rule() as any);
        expect(p1.tags).toEqual(['hello']);
        const p2 = buildCreatePayload(baseFields({tags: []}), rule() as any);
        expect(p2.tags).toBeUndefined();
    });

    it('includes link_uuid only when requiresPair=true', () => {
        const p1 = buildCreatePayload(baseFields({link_uuid: 'abc'}), rule({requiresPair: true}) as any);
        expect(p1.link_uuid).toBe('abc');
        const p2 = buildCreatePayload(baseFields({link_uuid: 'abc'}), rule({requiresPair: false}) as any);
        expect(p2.link_uuid).toBeUndefined();
    });

    it('applies sign rules to quantity', () => {
        const p = buildCreatePayload(baseFields({quantity: '10'}), rule({quantityRule: 'negative'}) as any);
        expect(p.quantity).toBe('-10');
    });
});

// =============================================================================
//  buildUpdateDiff
// =============================================================================

describe('buildUpdateDiff', () => {
    it('returns only {id} when nothing changed', () => {
        const fields = baseFields();
        const orig = baseOriginal();
        const diff = buildUpdateDiff(fields, orig, rule() as any, rule() as any);
        expect(Object.keys(diff)).toEqual(['id']);
    });

    it('detects type change', () => {
        const diff = buildUpdateDiff(baseFields({type: 'SELL'}), baseOriginal(), rule() as any, rule() as any);
        expect(diff.type).toBe('SELL');
    });

    it('detects quantity change with sign normalization', () => {
        const diff = buildUpdateDiff(baseFields({quantity: '20'}), baseOriginal({quantity: '10'}), rule() as any, rule() as any);
        expect(diff.quantity).toBe('20');
    });

    it('detects tags change ignoring order', () => {
        const diff = buildUpdateDiff(baseFields({tags: ['b', 'a']}), baseOriginal({tags: ['a', 'b']}), rule() as any, rule() as any);
        expect(diff.tags).toBeUndefined(); // same after sort → no diff
    });

    it('detects actual tags addition', () => {
        const diff = buildUpdateDiff(baseFields({tags: ['new']}), baseOriginal({tags: []}), rule() as any, rule() as any);
        expect(diff.tags).toEqual(['new']);
    });
});

// =============================================================================
//  diffDualItem
// =============================================================================

describe('diffDualItem', () => {
    it('returns only {id} when item matches original', () => {
        const item = {type: 'BUY', date: '2024-06-01', quantity: '10', cash: cash('EUR', '100')};
        const orig = baseOriginal();
        const diff = diffDualItem(item, orig);
        expect(Object.keys(diff)).toEqual(['id']);
    });

    it('detects changed fields from PATCHABLE_FIELDS only', () => {
        const item = {type: 'SELL', date: '2024-06-02', broker_id: 999};
        const orig = baseOriginal();
        const diff = diffDualItem(item, orig);
        expect(diff.type).toBe('SELL');
        expect(diff.date).toBe('2024-06-02');
        // broker_id is NOT patchable — should not appear
        expect(diff.broker_id).toBeUndefined();
    });
});

// =============================================================================
//  buildDualCreatePayloads
// =============================================================================

describe('buildDualCreatePayloads', () => {
    const from: TxFields = baseFields({type: 'TRANSFER', quantity: '100', cash: cash('EUR', '500')});
    const to: TxDualSide = {broker_id: 2, date: '2024-06-02'};

    it('fx layout: both items have type FX_CONVERSION', () => {
        const [f, t] = buildDualCreatePayloads('fx', {...from, cash: cash('EUR', '500')}, {broker_id: 2, cash: cash('USD', '550')}, 'uuid-1');
        expect(f.type).toBe('FX_CONVERSION');
        expect(t.type).toBe('FX_CONVERSION');
        expect(f.link_uuid).toBe('uuid-1');
        expect(t.link_uuid).toBe('uuid-1');
    });

    it('fx layout: from cash is negative, to cash is positive', () => {
        const [f, t] = buildDualCreatePayloads('fx', {...from, cash: cash('EUR', '500')}, {broker_id: 2, cash: cash('USD', '550')}, 'uuid-1');
        expect(Number((f.cash as CashValue).amount)).toBeLessThan(0);
        expect(Number((t.cash as CashValue).amount)).toBeGreaterThan(0);
    });

    it('transfer_asset layout: from qty negative, to qty positive', () => {
        const [f, t] = buildDualCreatePayloads('transfer_asset', {...from, quantity: '100'}, {broker_id: 2}, 'uuid-2');
        expect(Number(f.quantity)).toBeLessThan(0);
        expect(Number(t.quantity)).toBeGreaterThan(0);
    });

    it('transfer_asset layout: shared asset_id', () => {
        const [f, t] = buildDualCreatePayloads('transfer_asset', {...from, asset_id: 42}, {broker_id: 2}, 'uuid-3');
        expect(f.asset_id).toBe(42);
        expect(t.asset_id).toBe(42);
    });

    it('transfer_cash layout: from cash negative, to cash positive', () => {
        const [f, t] = buildDualCreatePayloads('transfer_cash', {...from, cash: cash('EUR', '500')}, {broker_id: 2}, 'uuid-4');
        expect(Number((f.cash as CashValue).amount)).toBeLessThan(0);
        expect(Number((t.cash as CashValue).amount)).toBeGreaterThan(0);
    });

    it('propagates tags and description to both sides', () => {
        const [f, t] = buildDualCreatePayloads('transfer_cash', {...from, tags: ['tag1'], description: 'desc'}, {broker_id: 2}, 'uuid-5');
        expect(f.tags).toEqual(['tag1']);
        expect(t.tags).toEqual(['tag1']);
        expect(f.description).toBe('desc');
        expect(t.description).toBe('desc');
    });
});

// =============================================================================
//  buildBatchPayload
// =============================================================================

describe('buildBatchPayload', () => {
    it('returns empty object for no ops/splits/promotes', () => {
        expect(buildBatchPayload({ops: []})).toEqual({});
    });

    it('aggregates create ops into creates[]', () => {
        const ops: ResolvedOp[] = [{intent: 'create', payload: {broker_id: 1, type: 'BUY'}}];
        const result = buildBatchPayload({ops});
        expect(result.creates).toHaveLength(1);
        expect(result.updates).toBeUndefined();
        expect(result.deletes).toBeUndefined();
    });

    it('includes partner payload in creates', () => {
        const ops: ResolvedOp[] = [{intent: 'create', payload: {type: 'A'}, partnerPayload: {type: 'B'}}];
        const result = buildBatchPayload({ops});
        expect(result.creates).toHaveLength(2);
    });

    it('aggregates update ops into updates[]', () => {
        const ops: ResolvedOp[] = [{intent: 'update', payload: {id: 1, type: 'SELL'}}];
        const result = buildBatchPayload({ops});
        expect(result.updates).toHaveLength(1);
    });

    it('aggregates delete ops into deletes[]', () => {
        const ops: ResolvedOp[] = [{intent: 'delete', deleteId: 10, partnerDeleteId: 11}];
        const result = buildBatchPayload({ops});
        expect(result.deletes).toEqual([10, 11]);
    });

    it('includes splits when provided', () => {
        const result = buildBatchPayload({ops: [], splits: [{id_a: 1, id_b: 2}]});
        expect(result.splits).toEqual([{id_a: 1, id_b: 2}]);
    });

    it('includes promotes when provided', () => {
        const result = buildBatchPayload({ops: [], promotes: [{id_a: 1, id_b: 2}]});
        expect(result.promotes).toEqual([{id_a: 1, id_b: 2}]);
    });

    it('omits keys with empty arrays', () => {
        const ops: ResolvedOp[] = [{intent: 'create', payload: {type: 'BUY'}}];
        const result = buildBatchPayload({ops, splits: [], promotes: []});
        expect(result.splits).toBeUndefined();
        expect(result.promotes).toBeUndefined();
    });

    it('mixed ops: all three categories', () => {
        const ops: ResolvedOp[] = [
            {intent: 'create', payload: {type: 'BUY'}},
            {intent: 'update', payload: {id: 5, date: '2024-01-01'}},
            {intent: 'delete', deleteId: 99},
        ];
        const result = buildBatchPayload({ops});
        expect(result.creates).toHaveLength(1);
        expect(result.updates).toHaveLength(1);
        expect(result.deletes).toEqual([99]);
    });
});

// =============================================================================
//  PATCHABLE_FIELDS constant
// =============================================================================

describe('PATCHABLE_FIELDS', () => {
    it('contains exactly the expected fields', () => {
        const expected = new Set(['type', 'date', 'quantity', 'cash', 'tags', 'description', 'cost_basis_override', 'asset_event_id']);
        expect(PATCHABLE_FIELDS).toEqual(expected);
    });

    it('does NOT contain immutable fields', () => {
        expect(PATCHABLE_FIELDS.has('broker_id')).toBe(false);
        expect(PATCHABLE_FIELDS.has('asset_id')).toBe(false);
        expect(PATCHABLE_FIELDS.has('link_uuid')).toBe(false);
    });
});
