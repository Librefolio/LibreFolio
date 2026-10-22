/**
 * Designer Lab — the state every tab shares (debug builds only).
 *
 * The state lives in localStorage under `STORAGE_KEY`. A write in one tab reaches every other tab of the same origin
 * through the `storage` event, so the Lab can sit in one window and the app in the others. The writing tab gets no
 * event and applies the state itself.
 */

import {CATEGORY_ROLES, lookupKey} from '$lib/theme/chartCategories';

import type {LabChange, LabState} from './types';

export const STORAGE_KEY = 'lf-designer-lab/v1';
export const STATE_SCHEMA = 'lf-designer-lab-state/1';

export function emptyState(): LabState {
    return {schema: STATE_SCHEMA, changes: [], suspended: false, cvd: 'none', notes: '', author: '', variants: {}, activeVariant: null, updatedAt: new Date().toISOString()};
}

/** The saved state, or null when there is none or it is not a state this version understands. */
export function readState(storage: Storage = localStorage): LabState | null {
    let raw: string | null;
    try {
        raw = storage.getItem(STORAGE_KEY);
    } catch {
        return null;
    }
    if (!raw) return null;
    try {
        const parsed = JSON.parse(raw) as Partial<LabState>;
        if (parsed?.schema !== STATE_SCHEMA || !Array.isArray(parsed.changes)) return null;
        return {...emptyState(), ...parsed, changes: parsed.changes.map(asRoleChange)} as LabState;
    } catch {
        return null;
    }
}

export function writeState(state: LabState, storage: Storage = localStorage): LabState {
    const next = {...state, updatedAt: new Date().toISOString()};
    storage.setItem(STORAGE_KEY, JSON.stringify(next));
    return next;
}

export function clearState(storage: Storage = localStorage): void {
    storage.removeItem(STORAGE_KEY);
}

/** Whether the state changes anything on screen. */
export function hasEffect(state: LabState | null): state is LabState {
    return !!state && !state.suspended && (state.changes.length > 0 || state.cvd !== 'none');
}

/**
 * The stable id of a change: one per layer, target, scope and (for a single stylesheet occurrence) occurrence. A
 * specialisation is one per property (and chart colour), scope and selector.
 */
export function changeId(change: Pick<LabChange, 'layer' | 'target' | 'scope' | 'occurrence' | 'property' | 'colorKey'>): string {
    if (change.layer === 'element') return `element:${change.property ?? ''}${change.colorKey ? `:${change.colorKey}` : ''}@${change.scope}~${change.target}`;
    const base = `${change.layer}:${change.target}@${change.scope}`;
    return change.occurrence === undefined ? base : `${base}#${change.occurrence}`;
}

/** Insert or replace a change (same id), keeping the order in which changes were first made. */
export function upsertChange(state: LabState, change: LabChange): LabState {
    const id = changeId(change);
    const next = {...change, id};
    const at = state.changes.findIndex((c) => c.id === id);
    const changes = at === -1 ? [...state.changes, next] : state.changes.map((c, i) => (i === at ? next : c));
    return {...state, changes};
}

export function removeChange(state: LabState, id: string): LabState {
    return {...state, changes: state.changes.filter((c) => c.id !== id)};
}

/** The changes that apply to a theme: those scoped to it and those scoped to both. */
export function changesForTheme(changes: LabChange[], dark: boolean): LabChange[] {
    return changes.filter((c) => c.scope === 'both' || (dark ? c.scope === 'dark' : c.scope === 'light'));
}

/** The role an asset type or the cash is drawn in, by the lookup key of its category target (`type:REALESTATE`). */
const ROLE_OF_CATEGORY = new Map(CATEGORY_ROLES.map((c) => [`${c.kind}:${lookupKey(c.key)}`, c.role]));

/**
 * A `category` change of an asset type or of the cash, as the Lab made it before DV-11, becomes a change of its role
 * (`css-var`): their colour is that role now, so an edit reaches the badges and the charts together. Any other change
 * comes back as it is. Applied to a saved state when it is read, and to an import.
 */
export function asRoleChange(change: LabChange): LabChange {
    if (change.layer !== 'category') return change;
    const m = /^(type|bucket):(.+)$/.exec(change.target);
    const role = m ? ROLE_OF_CATEGORY.get(`${m[1]}:${lookupKey(m[2])}`) : undefined;
    if (!role) return change;
    const next: LabChange = {...change, layer: 'css-var', target: role};
    return {...next, id: changeId(next)};
}
