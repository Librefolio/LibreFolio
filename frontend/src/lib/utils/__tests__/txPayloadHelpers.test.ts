/**
 * Unit tests for txPayloadHelpers — pure payload building functions.
 */
import {describe, expect, it, vi} from 'vitest';

const {getCostBasisRuleMock} = vi.hoisted(() => ({
    getCostBasisRuleMock: vi.fn((type: string, side?: 'from' | 'to' | 'self') => {
        if (type === 'SIDE_PROBE') return 'optional';
        if (type === 'REQUIRED_POSITIVE') return 'required_qty_pos';
        if (type === 'TRANSFER') return side === 'to' ? 'required_qty_pos' : 'forbidden';
        return 'forbidden';
    }),
}));

vi.mock('$lib/stores/transactions/transactionTypeStore', () => ({
    getCostBasisRule: getCostBasisRuleMock,
}));

import {applySign, applySignRules, buildSignedCash, exactDecimalEqual, exactDecimalSign, fieldEq, buildCreatePayload, buildUpdateDiff, diffDualItem, buildDualCreatePayloads, buildBatchPayload, PATCHABLE_FIELDS, signedCashAmount, upgradeAutoToDetail} from '../transactions/txPayloadHelpers';
import type {TxFields, TxOriginal, CashValue, ResolvedOp, TxDualSide} from '../transactions/txPayloadHelpers';

// =============================================================================
//  Mock TypeRule factory
// =============================================================================

interface MockRule {
    quantityRule: 'positive' | 'negative' | 'zero' | 'free' | 'any';
    cashSign: 'positive' | 'negative' | 'optional' | 'free' | 'any';
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
//  Exact decimal sign/equality primitives
// =============================================================================

describe('applySign', () => {
    it('signs the 12+6 maximum without routing its digits through Number', () => {
        expect(applySign('999999999999.123456', 'negative')).toBe('-999999999999.123456');
        expect(applySign('-999999999999.123456', 'positive')).toBe('999999999999.123456');
    });

    it.each([
        ['+0001.230000', 'positive', '0001.230000'],
        ['+0001.230000', 'negative', '-0001.230000'],
        ['.000001', 'positive', '.000001'],
        ['.000001', 'negative', '-.000001'],
        ['-0.000000', 'positive', '0.000000'],
        ['-0.000000', 'negative', '0.000000'],
        ['', 'positive', '0'],
        ['', 'negative', '0'],
    ])('applySign(%j, %s) preserves exact representation as %j', (value, signRule, expected) => {
        expect(applySign(value, signRule)).toBe(expected);
    });

    it.each(['abc', '1e3', '1,25', '-', '+', '.'])('leaves invalid or partial %j unchanged', (value) => {
        expect(applySign(value, 'positive')).toBe(value);
        expect(applySign(value, 'negative')).toBe(value);
    });

    it.each(['999999999999.123456', '-0001.230000', '+.000001', '-0.000000', '1e3'])('leaves free-sign %j byte-for-byte unchanged', (value) => {
        expect(applySign(value, 'free')).toBe(value);
    });
});

describe('exactDecimalSign', () => {
    it.each(['1', '+1', '0001.230000', '.000001', '999999999999.123456'])('classifies %j as positive', (value) => {
        expect(exactDecimalSign(value)).toBe(1);
    });

    it.each(['-1', '-0001.230000', '-.000001', '-999999999999.123456'])('classifies %j as negative', (value) => {
        expect(exactDecimalSign(value)).toBe(-1);
    });

    it.each(['0', '-0', '+0.000000', '000.000', '0.'])('classifies %j as zero', (value) => {
        expect(exactDecimalSign(value)).toBe(0);
    });

    it.each([null, undefined, 1, '', ' ', '-', '+', '.', '1e3', '1,2', '—'])('returns null for partial or invalid %j', (value) => {
        expect(exactDecimalSign(value)).toBeNull();
    });
});

describe('exactDecimalEqual', () => {
    it.each([
        ['0001.230000', '1.23'],
        ['.5', '0.5'],
        ['1.', '1.000000'],
        ['-0.000000', '+0'],
        [' 0001.2300 ', '1.23'],
    ])('treats %j and %j as the same exact decimal', (left, right) => {
        expect(exactDecimalEqual(left, right)).toBe(true);
    });

    it('distinguishes adjacent values at the 12+6 boundary', () => {
        expect(exactDecimalEqual('999999999999.123456', '999999999999.123457')).toBe(false);
    });

    it('falls back to strict equality when either input is not a plain decimal', () => {
        expect(exactDecimalEqual('1e3', '1e3')).toBe(true);
        expect(exactDecimalEqual('1e3', '1000')).toBe(false);
        expect(exactDecimalEqual('1,25', '1.25')).toBe(false);
        expect(exactDecimalEqual(null, null)).toBe(true);
        expect(exactDecimalEqual(null, undefined)).toBe(false);
    });
});

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

    it('forces a positive rule too, not only a negative one', () => {
        // A "positive" rule binds exactly as hard as a "negative" one: the backend rejects
        // `BUY requires quantity > 0` the same way it rejects `SELL requires quantity < 0`.
        const r = rule({quantityRule: 'positive', cashSign: 'positive'});
        const {signedQty, signedCash} = applySignRules('-10', cash('EUR', '-100'), r as any);
        expect(signedQty).toBe('10');
        expect(signedCash?.amount).toBe('100');
    });

    it('leaves a free-sign rule alone in both directions', () => {
        // On ADJUSTMENT and TRANSFER the sign *is* the information — it says which way the
        // position moved — so coercing it would silently reverse the user's meaning.
        const r = rule({quantityRule: 'free', cashSign: 'any'});
        expect(applySignRules('-10', cash('EUR', '-100'), r as any).signedQty).toBe('-10');
        expect(applySignRules('-10', cash('EUR', '-100'), r as any).signedCash?.amount).toBe('-100');
    });

    it('retypes a deposit into a sale with the sale sign', () => {
        // The import wizard case: a fund redemption arrives as a deposit, the user retypes it
        // to SELL and states the units as a magnitude. Sending them unsigned failed the whole
        // duplicate re-check with "SELL requires quantity < 0".
        const r = rule({quantityRule: 'negative', cashSign: 'positive'});
        const {signedQty, signedCash} = applySignRules('1867.178', cash('EUR', '9984.47'), r as any);
        expect(signedQty).toBe('-1867.178');
        expect(signedCash?.amount).toBe('9984.47');
    });

    it('returns null cash when input is null', () => {
        const {signedCash} = applySignRules('5', null, rule() as any);
        expect(signedCash).toBeNull();
    });

    it('leaves an unparsable quantity as typed rather than inventing a number for it', () => {
        // Coercion is a sign correction, not a parser: swallowing a malformed value here
        // would hide it from the validator that is meant to report it. An empty string is
        // the exception: signed fields preserve the established explicit zero fallback.
        const r = rule({quantityRule: 'negative', cashSign: 'negative'});
        expect(applySignRules('abc', cash('EUR', 'abc'), r as any).signedQty).toBe('abc');
        expect(applySignRules('abc', cash('EUR', 'abc'), r as any).signedCash?.amount).toBe('abc');
        expect(applySignRules('', cash('EUR', ''), r as any).signedQty).toBe('0');
    });

    it('never touches the currency, only the sign', () => {
        const r = rule({quantityRule: 'negative', cashSign: 'negative'});
        expect(applySignRules('10', cash('CHF', '100'), r as any).signedCash?.code).toBe('CHF');
    });

    it('keeps a zero unsigned, since -0 would serialise as "-0"', () => {
        const r = rule({quantityRule: 'negative', cashSign: 'negative'});
        expect(applySignRules('-0.000000', cash('EUR', '-0.00'), r as any)).toEqual({
            signedQty: '0.000000',
            signedCash: {code: 'EUR', amount: '0.00'},
        });
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
//  signedCashAmount legacy number API
// =============================================================================

describe('signedCashAmount', () => {
    it('keeps its established number return API for valid cash', () => {
        expect(signedCashAmount(cash('USD', '12.5'), rule({cashSign: 'negative'}) as any)).toBe(-12.5);
        expect(signedCashAmount(cash('USD', '-12.5'), rule({cashSign: 'positive'}) as any)).toBe(12.5);
    });

    it('returns null for absent or non-finite cash', () => {
        expect(signedCashAmount(null, rule() as any)).toBeNull();
        expect(signedCashAmount(cash('USD', '1e999'), rule() as any)).toBeNull();
        expect(signedCashAmount(cash('USD', 'not-cash'), rule() as any)).toBeNull();
    });
});

// =============================================================================
//  fieldEq
// =============================================================================

describe('fieldEq', () => {
    it.each([
        {key: 'quantity', a: '10', b: '10.000000', expected: true},
        {key: 'quantity', a: '0001.230000', b: '1.23', expected: true},
        {key: 'quantity', a: '999999999999.123456', b: '999999999999.123457', expected: false},
        {key: 'quantity', a: '10', b: '11', expected: false},
        {key: 'cash', a: cash('EUR', '1.5'), b: cash('EUR', '1.500'), expected: true},
        {key: 'cash', a: cash('EUR', '0001.230000'), b: cash('EUR', '1.23'), expected: true},
        {key: 'cash', a: cash('EUR', '999999999999.123456'), b: cash('EUR', '999999999999.123457'), expected: false},
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

    it.each([
        ['999999999999.123456', 'to'],
        ['-999999999999.123456', 'from'],
        ['-0.000000', 'self'],
        ['not-a-decimal', 'self'],
    ] as const)('chooses cost-basis side %s → %s from the exact quantity sign', (quantity, expectedSide) => {
        getCostBasisRuleMock.mockClear();
        const payload = buildCreatePayload(
            baseFields({
                type: 'SIDE_PROBE',
                quantity,
                cost_basis_mode: 'auto',
                cost_basis_override: cash('EUR', '0'),
            }),
            rule({quantityRule: 'free'}) as any,
        );

        expect(getCostBasisRuleMock).toHaveBeenLastCalledWith('SIDE_PROBE', expectedSide);
        expect(payload.cost_basis_mode).toBe('auto');
    });

    it.each([
        ['0.000001', true],
        ['999999999999.123456', true],
        ['0', false],
        ['-0.000000', false],
        ['-0.000001', false],
        ['1e3', false],
    ] as const)('gates explicit auto/manual create and update cost basis by exact positive %j', (quantity, allowed) => {
        const autoOverride = cash('EUR', '0');
        const manualOverride = cash('EUR', '123.450000');
        const exactRule = rule({quantityRule: 'free'});
        const original = baseOriginal({
            type: 'REQUIRED_POSITIVE',
            quantity,
            cost_basis_override: null,
        });
        const commonFields = {
            type: 'REQUIRED_POSITIVE',
            quantity,
        } as const;
        const autoFields = baseFields({...commonFields, cost_basis_mode: 'auto', cost_basis_override: autoOverride});
        const manualFields = baseFields({...commonFields, cost_basis_mode: 'manual', cost_basis_override: manualOverride});
        const autoCreate = buildCreatePayload(autoFields, exactRule as any);
        const autoUpdate = buildUpdateDiff(autoFields, original, exactRule as any, exactRule as any);
        const manualCreate = buildCreatePayload(manualFields, exactRule as any);
        const manualUpdate = buildUpdateDiff(manualFields, original, exactRule as any, exactRule as any);

        expect('cost_basis_mode' in autoCreate).toBe(allowed);
        expect('cost_basis_override' in autoCreate).toBe(allowed);
        expect('cost_basis_mode' in autoUpdate).toBe(allowed);
        expect('cost_basis_override' in autoUpdate).toBe(allowed);
        expect('cost_basis_mode' in manualCreate).toBe(false);
        expect('cost_basis_override' in manualCreate).toBe(allowed);
        expect('cost_basis_mode' in manualUpdate).toBe(false);
        expect('cost_basis_override' in manualUpdate).toBe(allowed);
        if (allowed) {
            expect(autoCreate.cost_basis_override).toEqual(autoOverride);
            expect(autoUpdate.cost_basis_override).toEqual(autoOverride);
            expect(manualCreate.cost_basis_override).toEqual(manualOverride);
            expect(manualUpdate.cost_basis_override).toEqual(manualOverride);
        }
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

    it('emits an adjacent high-precision quantity update without losing the last digit', () => {
        const diff = buildUpdateDiff(baseFields({quantity: '999999999999.123456'}), baseOriginal({quantity: '999999999999.123455'}), rule() as any, rule() as any);
        expect(diff.quantity).toBe('999999999999.123456');
    });

    it('does not emit a quantity update for representation-only zeros', () => {
        const diff = buildUpdateDiff(baseFields({quantity: '0001.230000'}), baseOriginal({quantity: '1.23'}), rule() as any, rule() as any);
        expect(diff).toEqual({id: 99});
    });

    it('emits the exact signed SELL quantity', () => {
        const sellRule = rule({quantityRule: 'negative'});
        const diff = buildUpdateDiff(baseFields({type: 'SELL', quantity: '999999999999.123456'}), baseOriginal({type: 'SELL', quantity: '-999999999999.123455'}), sellRule as any, sellRule as any);
        expect(diff.quantity).toBe('-999999999999.123456');
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
    const autoSentinel = cash('EUR', '0');
    const manualOverride = cash('EUR', '123.450000');

    it('fx layout: both items have type FX_CONVERSION', () => {
        const [f, t] = buildDualCreatePayloads('fx', {...from, cash: cash('EUR', '500')}, {broker_id: 2, cash: cash('USD', '550')}, 'uuid-1');
        expect(f.type).toBe('FX_CONVERSION');
        expect(t.type).toBe('FX_CONVERSION');
        expect(f.link_uuid).toBe('uuid-1');
        expect(t.link_uuid).toBe('uuid-1');
    });

    it('fx layout: from cash is negative, to cash is positive', () => {
        const [f, t] = buildDualCreatePayloads('fx', {...from, cash: cash('EUR', '500')}, {broker_id: 2, cash: cash('USD', '550')}, 'uuid-1');
        expect((f.cash as CashValue).amount).toBe('-500');
        expect((t.cash as CashValue).amount).toBe('550');
    });

    it.each([
        ['allowed auto receiver', '100', 'auto', autoSentinel, autoSentinel, 'auto', autoSentinel],
        ['allowed manual receiver', '100', 'manual', manualOverride, cash('EUR', '10'), undefined, manualOverride],
        ['disallowed zero auto receiver', '0.000000', 'auto', autoSentinel, autoSentinel, undefined, undefined],
        ['disallowed zero manual receiver', '0.000000', 'manual', manualOverride, cash('EUR', '10'), undefined, undefined],
    ] as const)('transfer_asset %s keeps paired cost basis atomic through direct-update diffing', (_label, quantity, mode, override, originalOverride, expectedMode, expectedOverride) => {
        const [fromItem, toItem] = buildDualCreatePayloads('transfer_asset', {...from, quantity, cost_basis_mode: mode, cost_basis_override: override}, {broker_id: 2}, 'uuid-2');
        expect(fromItem.quantity).toBe(applySign(quantity, 'negative'));
        expect(toItem.quantity).toBe(applySign(quantity, 'positive'));
        expect(fromItem).not.toHaveProperty('cost_basis_mode');
        expect(fromItem).not.toHaveProperty('cost_basis_override');

        const fromOriginal = baseOriginal({
            id: 101,
            type: 'TRANSFER',
            date: String(fromItem.date),
            quantity: String(fromItem.quantity),
            cash: null,
            cost_basis_override: null,
        });
        const toOriginal = baseOriginal({
            id: 202,
            type: 'TRANSFER',
            date: String(toItem.date),
            quantity: String(toItem.quantity),
            cash: null,
            cost_basis_override: originalOverride,
        });

        // Even contaminated sender input cannot leak cost basis onto the
        // metadata-forbidden leg.
        expect(
            diffDualItem(
                {
                    ...fromItem,
                    cost_basis_mode: mode,
                    cost_basis_override: override,
                },
                fromOriginal,
                mode,
            ),
        ).toEqual({id: 101});

        const expectedReceiverDiff: Record<string, unknown> = {id: 202};
        if (expectedMode) expectedReceiverDiff.cost_basis_mode = expectedMode;
        if (expectedOverride) expectedReceiverDiff.cost_basis_override = expectedOverride;
        expect(diffDualItem(toItem, toOriginal, mode)).toEqual(expectedReceiverDiff);
    });

    it('transfer_asset preserves all 12+6 digits and never invents negative zero', () => {
        const [fromHigh, toHigh] = buildDualCreatePayloads('transfer_asset', {...from, quantity: '999999999999.123456'}, {broker_id: 2}, 'uuid-high');
        expect([fromHigh.quantity, toHigh.quantity]).toEqual(['-999999999999.123456', '999999999999.123456']);

        const [fromZero, toZero] = buildDualCreatePayloads('transfer_asset', {...from, quantity: '-0.000000'}, {broker_id: 2}, 'uuid-zero');
        expect([fromZero.quantity, toZero.quantity]).toEqual(['0.000000', '0.000000']);
    });

    it('transfer_asset layout: shared asset_id', () => {
        const [f, t] = buildDualCreatePayloads('transfer_asset', {...from, asset_id: 42}, {broker_id: 2}, 'uuid-3');
        expect(f.asset_id).toBe(42);
        expect(t.asset_id).toBe(42);
    });

    it('transfer_cash layout: from cash negative, to cash positive', () => {
        const [f, t] = buildDualCreatePayloads('transfer_cash', {...from, cash: cash('EUR', '500')}, {broker_id: 2}, 'uuid-4');
        expect((f.cash as CashValue).amount).toBe('-500');
        expect((t.cash as CashValue).amount).toBe('500');
    });

    it('FX and cash-transfer legs preserve trailing zeros and pair order', () => {
        const [fxFrom, fxTo] = buildDualCreatePayloads('fx', {...from, cash: cash('EUR', '001.2300')}, {broker_id: 2, cash: cash('USD', '000.5000')}, 'uuid-fx');
        expect([fxFrom.cash, fxTo.cash]).toEqual([
            {code: 'EUR', amount: '-001.2300'},
            {code: 'USD', amount: '000.5000'},
        ]);

        const [cashFrom, cashTo] = buildDualCreatePayloads('transfer_cash', {...from, cash: cash('EUR', '001.2300')}, {broker_id: 2}, 'uuid-cash');
        expect([cashFrom.cash, cashTo.cash]).toEqual([
            {code: 'EUR', amount: '-001.2300'},
            {code: 'EUR', amount: '001.2300'},
        ]);
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

    it('preserves create/partner, update/partner, delete, split, and promote order', () => {
        const ops: ResolvedOp[] = [
            {intent: 'create', payload: {type: 'BUY'}, partnerPayload: {type: 'SELL'}},
            {intent: 'update', payload: {id: 5, date: '2024-01-01'}, partnerPayload: {id: 6, date: '2024-01-02'}},
            {intent: 'delete', deleteId: 99, partnerDeleteId: 100},
        ];
        expect(
            buildBatchPayload({
                ops,
                splits: [
                    {id_a: 7, id_b: 8},
                    {id_a: 9, id_b: 10},
                ],
                promotes: [
                    {id_a: 11, id_b: 12},
                    {id_a: 13, id_b: 14},
                ],
            }),
        ).toEqual({
            creates: [{type: 'BUY'}, {type: 'SELL'}],
            updates: [
                {id: 5, date: '2024-01-01'},
                {id: 6, date: '2024-01-02'},
            ],
            deletes: [99, 100],
            splits: [
                {id_a: 7, id_b: 8},
                {id_a: 9, id_b: 10},
            ],
            promotes: [
                {id_a: 11, id_b: 12},
                {id_a: 13, id_b: 14},
            ],
        });
    });
});

// =============================================================================
//  validate-only WAC promotion
// =============================================================================

describe('upgradeAutoToDetail', () => {
    it('promotes auto creates/updates in place without changing shape or order', () => {
        const payload: Record<string, unknown> = {
            creates: [
                {type: 'BUY', cost_basis_mode: 'auto', quantity: '1'},
                {type: 'SELL', quantity: '-1'},
            ],
            updates: [
                {id: 7, cost_basis_mode: 'manual'},
                {id: 8, cost_basis_mode: 'auto'},
            ],
            deletes: [9],
            promotes: [{id_a: 10, id_b: 11}],
        };

        upgradeAutoToDetail(payload);

        expect(payload).toEqual({
            creates: [
                {type: 'BUY', cost_basis_mode: 'auto-detail', quantity: '1'},
                {type: 'SELL', quantity: '-1'},
            ],
            updates: [
                {id: 7, cost_basis_mode: 'manual'},
                {id: 8, cost_basis_mode: 'auto-detail'},
            ],
            deletes: [9],
            promotes: [{id_a: 10, id_b: 11}],
        });
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
