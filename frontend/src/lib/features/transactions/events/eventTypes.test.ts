import {describe, it, expect} from 'vitest';
import {getEventTypeOptions, EVENT_TYPES_ALL, EVENT_TYPES_TX_COMPATIBLE, EVENT_TYPES_FOR_ADJUSTMENT, eventTypesForTx, defaultEventTypeForTx} from './eventTypes';

/**
 * `getEventTypeEmoji` reads a module cache that is empty in a unit run, so it
 * returns the '📌' fallback for every type. We assert on structure, not on the
 * specific glyph — the emoji source is a store, tested elsewhere.
 */
describe('getEventTypeOptions', () => {
    it('builds one option per type for all five when no filter is given', () => {
        const t = (key: string) => key; // key echo → non-empty labels/tooltips
        const opts = getEventTypeOptions(t);
        expect(opts.map((o) => o.value)).toEqual([...EVENT_TYPES_ALL]);
        // Every option is fully populated with a docs path from the internal map.
        for (const o of opts) {
            expect(o.docsPath).toMatch(/asset-events\//);
            expect(o.emoji.length).toBeGreaterThan(0);
        }
    });

    it('honours an explicit filter (TX-compatible subset)', () => {
        const t = (key: string) => key;
        const opts = getEventTypeOptions(t, EVENT_TYPES_TX_COMPATIBLE);
        expect(opts.map((o) => o.value)).toEqual([...EVENT_TYPES_TX_COMPATIBLE]);
    });

    it('uses the i18n label and tooltip when translation returns a non-empty string', () => {
        const t = (key: string) => (key.includes('eventTypeTooltip') ? 'A tooltip' : 'A label');
        const [opt] = getEventTypeOptions(t, ['DIVIDEND']);
        expect(opt.label).toBe('A label');
        expect(opt.tooltip).toBe('A tooltip');
    });

    it('falls back to a de-underscored type name when the label translation is empty', () => {
        const t = () => ''; // empty → both `|| type.replace` and `|| undefined` branches
        const [opt] = getEventTypeOptions(t, ['PRICE_ADJUSTMENT']);
        expect(opt.label).toBe('PRICE ADJUSTMENT');
        expect(opt.tooltip).toBeUndefined();
    });

    it('leaves docsPath undefined for a type absent from the docs map', () => {
        const t = (key: string) => key;
        const [opt] = getEventTypeOptions(t, ['NOT_A_REAL_TYPE']);
        expect(opt.docsPath).toBeUndefined();
        expect(opt.value).toBe('NOT_A_REAL_TYPE');
    });
});

/**
 * W-B87 — an ADJUSTMENT row is linked to a SPLIT (or a PRICE_ADJUSTMENT), the other types keep the three
 * TX-compatible events. The two helpers decide which events the mini modal offers and which one it starts on.
 */
describe('EVENT_TYPES_FOR_ADJUSTMENT', () => {
    it('is SPLIT then PRICE_ADJUSTMENT, the two types the backend takes for an ADJUSTMENT', () => {
        expect([...EVENT_TYPES_FOR_ADJUSTMENT]).toEqual(['SPLIT', 'PRICE_ADJUSTMENT']);
    });

    it('guard: the TX-compatible list is unchanged', () => {
        expect([...EVENT_TYPES_TX_COMPATIBLE]).toEqual(['DIVIDEND', 'INTEREST', 'PRICE_ADJUSTMENT']);
    });
});

describe('eventTypesForTx', () => {
    it('gives an ADJUSTMENT the SPLIT and PRICE_ADJUSTMENT events', () => {
        expect([...eventTypesForTx('ADJUSTMENT')]).toEqual([...EVENT_TYPES_FOR_ADJUSTMENT]);
    });

    it.each(['DIVIDEND', 'INTEREST', 'BUY', 'SELL', 'DEPOSIT', 'TRANSFER', ''])('gives %j the unchanged TX-compatible events', (txType) => {
        expect([...eventTypesForTx(txType)]).toEqual([...EVENT_TYPES_TX_COMPATIBLE]);
    });
});

describe('defaultEventTypeForTx', () => {
    it.each([
        ['ADJUSTMENT', 'SPLIT'],
        ['INTEREST', 'INTEREST'],
        ['DIVIDEND', 'DIVIDEND'],
        ['BUY', 'DIVIDEND'],
        ['TRANSFER', 'DIVIDEND'],
        ['', 'DIVIDEND'],
    ])('%j starts on %s', (txType, expected) => {
        expect(defaultEventTypeForTx(txType)).toBe(expected);
    });

    it('the default is always one of the types on offer for that row', () => {
        for (const txType of ['ADJUSTMENT', 'INTEREST', 'DIVIDEND']) {
            expect(eventTypesForTx(txType)).toContain(defaultEventTypeForTx(txType));
        }
    });
});
