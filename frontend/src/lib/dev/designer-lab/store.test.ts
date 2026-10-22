/**
 * Designer Lab — the state every tab shares (`store.ts`).
 *
 * The Lab writes its changes to localStorage and every other tab re-applies them, so the stored form is a contract
 * between tabs (and between versions of the Lab): what an unknown or broken entry gives, how a change is identified,
 * and in which order changes are kept. Storage is an in-memory `Storage` passed as the parameter the functions take,
 * so no global is touched; the one clock read (`updatedAt`) runs under a fixed system time.
 */

import {afterEach, describe, expect, it, vi} from 'vitest';
import {asRoleChange, changeId, changesForTheme, clearState, emptyState, hasEffect, readState, removeChange, STATE_SCHEMA, STORAGE_KEY, upsertChange, writeState} from './store';
import type {LabAnchor, LabChange, LabState} from './types';

/** A `Storage` held in a Map: what one browser profile's localStorage is to the functions under test. */
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

/** A storage the browser refuses (private mode, a sandboxed frame, a quota error): every call throws. */
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

const ANCHOR: LabAnchor = {
    route: '/transactions',
    theme: 'light',
    testids: ['tx-table'],
    css_path: '[data-testid="tx-table"] > div > table > thead > tr > th:nth-of-type(2)',
    element: {tag: 'th', classes: [], scope_class: 'svelte-1x2y3z'},
    selector: '[data-testid="tx-table"] > div > table > thead > tr > th',
    breadth: 'component',
    matches: 12,
    property: 'color',
    computed: 'rgb(100, 116, 139)',
    source: {kind: 'rule-literal', selector: 'th', var: null, class: null},
    candidates: [{file: 'src/lib/components/table/DataTable.svelte', line: 1607, why: 'matched-rule', needle: '#64748b'}],
};

/** A change as the editor builds it, before `upsertChange` gives it its id. */
const change = (fields: Partial<LabChange> & Pick<LabChange, 'layer' | 'target' | 'scope'>): LabChange => ({id: '', from: '', to: '#dc2626', ...fields});

const stateWith = (changes: LabChange[], extra: Partial<LabState> = {}): LabState => ({...emptyState(), changes, ...extra});

afterEach(() => {
    vi.useRealTimers();
});

describe('readState / writeState / clearState', () => {
    it('reads nothing from a storage where the Lab never wrote', () => {
        expect(readState(memoryStorage())).toBeNull();
    });

    it('writes the state as JSON under its key, stamps `updatedAt`, and reads back what it wrote', () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-10-14T18:30:00.000Z'));
        const storage = memoryStorage();
        const state = upsertChange(stateWith([], {notes: 'darker table headers', author: 'designer', cvd: 'deuteranopia', updatedAt: '2026-10-01T08:00:00.000Z'}), change({layer: 'css-var', target: '--color-gray-500', scope: 'both'}));

        const written = writeState(state, storage);

        expect(written).toEqual({...state, updatedAt: '2026-10-14T18:30:00.000Z'});
        expect(JSON.parse(storage.getItem(STORAGE_KEY) ?? 'null')).toEqual(written);
        expect(readState(storage)).toEqual(written);
        // The caller's object is left as it was.
        expect(state.updatedAt).toBe('2026-10-01T08:00:00.000Z');
    });

    it('fills the fields an older state lacks from the empty state', () => {
        const storage = memoryStorage({[STORAGE_KEY]: JSON.stringify({schema: STATE_SCHEMA, changes: []})});
        expect(readState(storage)).toMatchObject({schema: STATE_SCHEMA, changes: [], suspended: false, cvd: 'none', notes: '', author: '', variants: {}, activeVariant: null});
    });

    it.each([
        ['another schema', JSON.stringify({schema: 'lf-designer-lab-state/0', changes: []})],
        ['changes that are not a list', JSON.stringify({schema: STATE_SCHEMA, changes: {}})],
        ['no changes at all', JSON.stringify({schema: STATE_SCHEMA})],
        ['JSON null', 'null'],
        ['a JSON string', '"lf-designer-lab-state/1"'],
        ['text that is not JSON', '{"schema": "lf-designer-lab-state/1", '],
        ['an empty string', ''],
    ])('reads null from %s', (_label, raw) => {
        expect(readState(memoryStorage({[STORAGE_KEY]: raw}))).toBeNull();
    });

    it('reads null, without throwing, from a storage that refuses to be read', () => {
        expect(readState(refusingStorage())).toBeNull();
    });

    it('clears its own key and nothing else', () => {
        const storage = memoryStorage({[STORAGE_KEY]: JSON.stringify(emptyState()), 'lf-other-key': 'kept'});
        clearState(storage);
        expect(storage.getItem(STORAGE_KEY)).toBeNull();
        expect(storage.getItem('lf-other-key')).toBe('kept');
        expect(readState(storage)).toBeNull();
    });
});

describe('asRoleChange — an asset type or the cash edited as a category before DV-11', () => {
    it('becomes a change of its role, its key read as the tables compare it', () => {
        expect(asRoleChange(change({layer: 'category', target: 'type:real_estate', scope: 'dark', to: '#123456'}))).toMatchObject({id: 'css-var:--lf-cat-real-estate@dark', layer: 'css-var', target: '--lf-cat-real-estate', scope: 'dark', to: '#123456'});
        expect(asRoleChange(change({layer: 'category', target: 'bucket:Liquidity', scope: 'both'}))).toMatchObject({id: 'css-var:--lf-cat-liquidity@both', layer: 'css-var', target: '--lf-cat-liquidity'});
    });

    it('leaves every other change as it is: a sector, «Unknown», a key outside the tables, another layer', () => {
        for (const other of [
            change({layer: 'category', target: 'sector:Health Care', scope: 'both'}),
            change({layer: 'category', target: 'bucket:Unknown', scope: 'both'}),
            change({layer: 'category', target: 'type:AAA', scope: 'both'}),
            change({layer: 'css-var', target: '--lf-cat-etf', scope: 'both'}),
        ]) {
            expect(asRoleChange(other), other.target).toBe(other);
        }
    });

    it('is applied to a saved state when it is read', () => {
        const legacy = {...change({layer: 'category', target: 'type:ETF', scope: 'light', to: '#123456'}), id: 'category:type:ETF@light'};
        const storage = memoryStorage({[STORAGE_KEY]: JSON.stringify({schema: STATE_SCHEMA, changes: [legacy]})});
        expect(readState(storage)?.changes).toEqual([{...legacy, layer: 'css-var', target: '--lf-cat-etf', id: 'css-var:--lf-cat-etf@light'}]);
    });
});

describe('hasEffect', () => {
    const one = [change({layer: 'css-var', target: '--color-gray-500', scope: 'both'})];

    it('is false without a state, and for a state that changes nothing', () => {
        expect(hasEffect(null)).toBe(false);
        expect(hasEffect(emptyState())).toBe(false);
    });

    it('is true for a change, and for a colour-vision simulation alone', () => {
        expect(hasEffect(stateWith(one))).toBe(true);
        expect(hasEffect(stateWith([], {cvd: 'protanopia'}))).toBe(true);
    });

    it('is false while the changes are suspended, whatever they hold', () => {
        expect(hasEffect(stateWith(one, {suspended: true}))).toBe(false);
        expect(hasEffect(stateWith(one, {suspended: true, cvd: 'achromatopsia'}))).toBe(false);
    });
});

describe('changeId', () => {
    it('identifies a change by layer, target and scope', () => {
        expect(changeId(change({layer: 'css-var', target: '--color-gray-500', scope: 'both'}))).toBe('css-var:--color-gray-500@both');
        expect(changeId(change({layer: 'css-literal', target: '#64748b', scope: 'light'}))).toBe('css-literal:#64748b@light');
        expect(changeId(change({layer: 'chart-color', target: '#10b981', scope: 'dark'}))).toBe('chart-color:#10b981@dark');
        expect(changeId(change({layer: 'proposal', target: '#0f172a', scope: 'both'}))).toBe('proposal:#0f172a@both');
    });

    it('adds the catalogue occurrence of a single stylesheet occurrence, the first one (id 0) included', () => {
        expect(changeId(change({layer: 'css-literal', target: '#64748b', scope: 'dark', occurrence: 12}))).toBe('css-literal:#64748b@dark#12');
        expect(changeId(change({layer: 'css-literal', target: '#64748b', scope: 'dark', occurrence: 0}))).toBe('css-literal:#64748b@dark#0');
    });

    it('identifies a specialisation by property, scope and selector, and a chart one by its colour too', () => {
        const selector = '[data-testid="tx-table"] > div > table > thead > tr > th';
        expect(changeId(change({layer: 'element', target: selector, scope: 'light', property: 'color'}))).toBe(`element:color@light~${selector}`);
        expect(changeId(change({layer: 'element', target: '[data-testid="growth-chart"]', scope: 'dark', property: 'chart', colorKey: '#10b981'}))).toBe('element:chart:#10b981@dark~[data-testid="growth-chart"]');
        // A specialisation is never narrowed to a catalogue occurrence.
        expect(changeId(change({layer: 'element', target: selector, scope: 'light', property: 'color', occurrence: 3}))).toBe(`element:color@light~${selector}`);
    });
});

describe('upsertChange / removeChange', () => {
    const gray = change({layer: 'css-var', target: '--color-gray-500', scope: 'both', to: '#475569'});
    const chart = change({layer: 'chart-color', target: '#10b981', scope: 'both'});
    const th = change({layer: 'element', target: '[data-testid="tx-table"] > th', scope: 'light', property: 'color', anchor: ANCHOR});

    it('gives a new change its id and appends it, without touching the state it was given', () => {
        const before = stateWith([]);
        const after = upsertChange(before, {...gray, id: 'ignored'});
        expect(after.changes).toEqual([{...gray, id: 'css-var:--color-gray-500@both'}]);
        expect(before.changes).toEqual([]);
    });

    it('replaces a change with the same id where it stands, keeping the order changes were first made in', () => {
        let state = stateWith([]);
        state = upsertChange(state, gray);
        state = upsertChange(state, chart);
        state = upsertChange(state, th);
        state = upsertChange(state, {...gray, to: '#334155', note: 'darker'});

        expect(state.changes.map((c) => c.id)).toEqual(['css-var:--color-gray-500@both', 'chart-color:#10b981@both', 'element:color@light~[data-testid="tx-table"] > th']);
        expect(state.changes[0]).toMatchObject({to: '#334155', note: 'darker'});
    });

    it('keeps apart changes that differ by scope, by occurrence, or by the selector of a specialisation', () => {
        let state = stateWith([]);
        for (const c of [gray, {...gray, scope: 'dark' as const}, change({layer: 'css-literal', target: '#64748b', scope: 'both'}), change({layer: 'css-literal', target: '#64748b', scope: 'both', occurrence: 4}), th, {...th, target: '[data-testid="tx-table"] > td'}]) {
            state = upsertChange(state, c);
        }
        expect(new Set(state.changes.map((c) => c.id)).size).toBe(6);
    });

    it('removes a change by id and leaves the others in order', () => {
        let state = stateWith([]);
        for (const c of [gray, chart, th]) state = upsertChange(state, c);
        const removed = removeChange(state, 'chart-color:#10b981@both');
        expect(removed.changes.map((c) => c.id)).toEqual(['css-var:--color-gray-500@both', 'element:color@light~[data-testid="tx-table"] > th']);
        expect(state.changes).toHaveLength(3);
        expect(removeChange(state, 'css-var:--unknown@both').changes).toEqual(state.changes);
    });
});

describe('changesForTheme', () => {
    const both = change({layer: 'css-var', target: '--a', scope: 'both'});
    const light = change({layer: 'css-var', target: '--b', scope: 'light'});
    const dark = change({layer: 'css-var', target: '--c', scope: 'dark'});

    it('applies to a theme the changes scoped to it and those scoped to both, in their order', () => {
        expect(changesForTheme([dark, both, light], true)).toEqual([dark, both]);
        expect(changesForTheme([dark, both, light], false)).toEqual([both, light]);
        expect(changesForTheme([], true)).toEqual([]);
    });
});
