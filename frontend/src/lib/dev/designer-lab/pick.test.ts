/**
 * Designer Lab — the element picker's messages between tabs (`pick.ts`).
 *
 * The Lab and the app tabs talk through one localStorage key: `start` (pick something), `cancel`, or `result` (the
 * element picked). A message is input from another tab, possibly of another version, so anything malformed must read
 * as no message; and a `start` left behind by a closed Lab must stop being answered after `PICK_FRESH_MS`. Freshness
 * is checked through the `now` parameter, never by waiting.
 */

import {afterEach, describe, expect, it, vi} from 'vitest';
import {isPendingStart, markSeen, newPickId, PICK_FRESH_MS, PICK_KEY, readPick, SEEN_KEY, wasSeen, writePick, type PickMessage} from './pick';
import type {PickedElement} from './types';

function memoryStorage(initial: Record<string, string> = {}): Storage {
    const data = new Map(Object.entries(initial));
    return {
        get length() {
            return data.size;
        },
        clear: () => data.clear(),
        getItem: (key: string) => data.get(key) ?? null,
        key: (index: number) => [...data.keys()][index] ?? null,
        removeItem: (key: string) => void data.delete(key),
        setItem: (key: string, value: string) => void data.set(key, String(value)),
    };
}

/** Private mode, a sandboxed frame, a full quota: every call throws. */
function refusingStorage(): Storage {
    const refuse = (): never => {
        throw new Error('storage refused');
    };
    return {
        get length(): number {
            return refuse();
        },
        clear: refuse,
        getItem: refuse,
        key: refuse,
        removeItem: refuse,
        setItem: refuse,
    };
}

const AT = Date.UTC(2026, 9, 14, 18, 0, 0);

const ELEMENT: PickedElement = {
    at: AT,
    route: '/transactions',
    theme: 'dark',
    testids: ['tx-table'],
    css_path: '[data-testid="tx-table"] > div > table > thead > tr > th:nth-of-type(2)',
    element: {tag: 'th', classes: ['sorted'], scope_class: 'svelte-1x2y3z'},
    selector: '[data-testid="tx-table"] > div > table > thead > tr > th',
    breadth: 'component',
    matches: 12,
    properties: [
        {
            property: 'color',
            computed: 'rgb(100, 116, 139)',
            colors: ['rgb(100, 116, 139)'],
            depth: 0,
            ancestor_tag: null,
            ancestor_testid: null,
            declarations: [{origin: 'rule', selector: 'th.svelte-1x2y3z', value: '#64748b', declared_as: 'color', important: false, layer: null, sheet: '0.C3P6fEz2.css', conditions: [], state: false, wins: true}],
            proved: true,
            current_color: false,
            lab_override: false,
            selector: '[data-testid="tx-table"] > div > table > thead > tr > th',
            breadth: 'component',
            matches: 12,
            at_ancestor: false,
        },
    ],
    chart: null,
};

afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
});

describe('readPick / writePick', () => {
    it.each<PickMessage>([
        {op: 'start', id: 'mf3k2a-x1y2z3', at: AT},
        {op: 'cancel', id: 'mf3k2a-x1y2z3', at: AT + 1_000},
        {op: 'result', id: 'mf3k2a-x1y2z3', at: AT + 2_000, element: ELEMENT},
    ])('reads back the $op message it wrote', (message) => {
        const storage = memoryStorage();
        writePick(message, storage);
        expect(storage.getItem(PICK_KEY)).not.toBeNull();
        expect(readPick(storage)).toEqual(message);
    });

    it('keeps only the fields of a start or cancel message', () => {
        const storage = memoryStorage({[PICK_KEY]: JSON.stringify({op: 'start', id: 'a-b', at: AT, element: ELEMENT, extra: true})});
        expect(readPick(storage)).toEqual({op: 'start', id: 'a-b', at: AT});
    });

    it.each([
        ['nothing written', null],
        ['an empty string', ''],
        ['text that is not JSON', '{"op": "start", '],
        ['JSON null', 'null'],
        ['an unknown op', JSON.stringify({op: 'pick', id: 'a-b', at: AT})],
        ['an id that is not a string', JSON.stringify({op: 'start', id: 42, at: AT})],
        ['a time that is not a number', JSON.stringify({op: 'start', id: 'a-b', at: '2026-10-14T18:00:00Z'})],
        ['a result without its element', JSON.stringify({op: 'result', id: 'a-b', at: AT})],
        ['a result whose element is not an object', JSON.stringify({op: 'result', id: 'a-b', at: AT, element: 'th'})],
    ])('reads null from %s', (_label, raw) => {
        expect(readPick(memoryStorage(raw === null ? {} : {[PICK_KEY]: raw}))).toBeNull();
    });

    it('neither reads nor writes through a storage that refuses, and never throws', () => {
        const storage = refusingStorage();
        expect(readPick(storage)).toBeNull();
        expect(() => writePick({op: 'start', id: 'a-b', at: AT}, storage)).not.toThrow();
    });
});

describe('isPendingStart', () => {
    const start: PickMessage = {op: 'start', id: 'a-b', at: AT};

    it('answers a start for PICK_FRESH_MS, and not a millisecond longer', () => {
        expect(isPendingStart(start, AT)).toBe(true);
        expect(isPendingStart(start, AT + PICK_FRESH_MS - 1)).toBe(true);
        expect(isPendingStart(start, AT + PICK_FRESH_MS)).toBe(false);
        expect(isPendingStart(start, AT + 24 * 60 * 60 * 1000)).toBe(false);
    });

    it('is never pending for a cancel, a result, or no message', () => {
        expect(isPendingStart({op: 'cancel', id: 'a-b', at: AT}, AT)).toBe(false);
        expect(isPendingStart({op: 'result', id: 'a-b', at: AT, element: ELEMENT}, AT)).toBe(false);
        expect(isPendingStart(null, AT)).toBe(false);
    });
});

describe('markSeen / wasSeen', () => {
    it('marks a browser where the Lab was opened, under its own key', () => {
        const storage = memoryStorage();
        expect(wasSeen(storage)).toBe(false);
        markSeen(storage);
        expect(wasSeen(storage)).toBe(true);
        expect(storage.getItem(SEEN_KEY)).not.toBeNull();
        expect(storage.getItem(PICK_KEY)).toBeNull();
    });

    it('reads a refusing storage as never seen, and marks it without throwing', () => {
        const storage = refusingStorage();
        expect(() => markSeen(storage)).not.toThrow();
        expect(wasSeen(storage)).toBe(false);
    });
});

describe('newPickId', () => {
    it('is the time in base 36 and a random part, both lower-case base 36', () => {
        vi.useFakeTimers();
        vi.setSystemTime(AT);
        vi.spyOn(Math, 'random').mockReturnValue(0.123456789);
        const id = newPickId();
        expect(id).toMatch(/^[0-9a-z]+-[0-9a-z]{1,6}$/);
        expect(id.split('-')[0]).toBe(AT.toString(36));
    });

    it('tells apart two ids made in the same millisecond', () => {
        vi.useFakeTimers();
        vi.setSystemTime(AT);
        vi.spyOn(Math, 'random').mockReturnValueOnce(0.123456789).mockReturnValueOnce(0.987654321);
        const first = newPickId();
        const second = newPickId();
        expect(first.split('-')[0]).toBe(second.split('-')[0]);
        expect(first).not.toBe(second);
    });
});
