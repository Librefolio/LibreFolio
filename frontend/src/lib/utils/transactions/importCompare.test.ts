// @vitest-environment node
import {describe, it, expect} from 'vitest';
import type {TransactionCreateItem} from '$lib/types';
import type {TXReadItem} from '$lib/components/transactions/types';
import {escHtml, compareTypeCellHtml, cmpSourceFromTx, cmpSourceFromExisting} from './importCompare';

const tx = (t: Record<string, unknown>): TransactionCreateItem => t as unknown as TransactionCreateItem;
const existing = (t: Record<string, unknown>): TXReadItem => t as unknown as TXReadItem;

describe('escHtml', () => {
    it('escapes only the three markup characters, leaving quotes intact', () => {
        expect(escHtml('1 < 2 & 3 > 4')).toBe('1 &lt; 2 &amp; 3 &gt; 4');
        expect(escHtml('say "hi" it\'s ok')).toBe('say "hi" it\'s ok');
    });

    it('escapes the ampersand first so it does not double-escape the others', () => {
        expect(escHtml('<')).toBe('&lt;');
        // A literal "&lt;" must not collapse into a real "<": the & is escaped, the rest kept.
        expect(escHtml('&lt;')).toBe('&amp;lt;');
    });
});

describe('compareTypeCellHtml', () => {
    it('derives the icon slug from the type (lowercased, underscores to dashes)', () => {
        const html = compareTypeCellHtml('CASH_IN', 'Contante');
        expect(html).toContain('/icons/transactions/cash-in.png');
    });

    it('renders the label the caller passed, HTML-escaped', () => {
        // The label is the caller's already-translated value, not something this fn invents.
        expect(compareTypeCellHtml('BUY', 'Acquisto')).toContain('<span>Acquisto</span>');
        expect(compareTypeCellHtml('BUY', '<b>x</b>')).toContain('<span>&lt;b&gt;x&lt;/b&gt;</span>');
    });
});

describe('cmpSourceFromTx', () => {
    it('unwraps an array-wrapped cash leg and asset id', () => {
        const s = cmpSourceFromTx(tx({date: '2024-05-01', type: 'BUY', cash: [{code: 'EUR', amount: '12.5'}], asset_id: [7], description: 'x'}));
        expect(s).toEqual({date: '2024-05-01', type: 'BUY', cashAmount: 12.5, cashCode: 'EUR', brokerId: null, assetId: 7, description: 'x'});
    });

    it('reads a plain object cash leg', () => {
        const s = cmpSourceFromTx(tx({type: 'SELL', cash: {code: 'USD', amount: -3}}));
        expect(s.cashAmount).toBe(-3);
        expect(s.cashCode).toBe('USD');
    });

    it('uses the fallback broker only when the row has none of its own', () => {
        expect(cmpSourceFromTx(tx({}), 9).brokerId).toBe(9);
        expect(cmpSourceFromTx(tx({broker_id: 3}), 9).brokerId).toBe(3);
    });

    it('nulls out an absent cash leg, a non-numeric asset id, and coerces missing fields', () => {
        const s = cmpSourceFromTx(tx({asset_id: 'not-a-number'}));
        expect(s.cashAmount).toBeNull();
        expect(s.cashCode).toBeNull();
        expect(s.assetId).toBeNull();
        expect(s.date).toBe('');
        expect(s.type).toBe('');
        expect(s.description).toBe('');
    });
});

describe('cmpSourceFromExisting', () => {
    it('collapses a stored transaction into the same neutral shape', () => {
        const s = cmpSourceFromExisting(existing({date: '2024-04-04', type: 'DIVIDEND', cash: {code: 'EUR', amount: '4.2'}, broker_id: 2, asset_id: 55, description: 'coupon'}));
        expect(s).toEqual({date: '2024-04-04', type: 'DIVIDEND', cashAmount: 4.2, cashCode: 'EUR', brokerId: 2, assetId: 55, description: 'coupon'});
    });

    it('nulls the amount when the stored row carries no cash', () => {
        const s = cmpSourceFromExisting(existing({date: '2024-04-04', type: 'ADJUSTMENT', cash: null, asset_id: 55}));
        expect(s.cashAmount).toBeNull();
        expect(s.cashCode).toBeNull();
        expect(s.brokerId).toBeNull();
    });

    it('blanks the date and type and nulls a non-numeric asset id on a sparse stored row', () => {
        // A stored row with empty date/type and no asset (e.g. a bare cash movement) must
        // still map cleanly rather than stringifying undefined.
        const s = cmpSourceFromExisting(existing({cash: {code: 'USD', amount: '1'}}));
        expect(s.date).toBe('');
        expect(s.type).toBe('');
        expect(s.assetId).toBeNull();
    });
});
