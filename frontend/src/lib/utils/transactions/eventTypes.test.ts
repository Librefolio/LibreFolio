import {describe, it, expect} from 'vitest';
import {getEventTypeOptions, EVENT_TYPES_ALL, EVENT_TYPES_TX_COMPATIBLE} from './eventTypes';

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
