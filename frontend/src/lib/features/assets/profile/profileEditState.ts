/**
 * profileEditState — the logic of the «Modifica i dati» window (plan 68, E10c), as pure functions: the window keeps
 * the DOM, the network and the comparison dialog; this module decides.
 *
 * - **Pending changes, keyed by voice** (`PendingChanges`): the shape the asset window holds (E8/E9) and hands to
 *   `PATCH /assets` as `profile`. A change is a value in the catalogue's stored form, «Lascia vuoto» (`emptied`), or
 *   «dalla fonte» (`source`: an enricher's value, saved in the source's name with what the user saw). `origin` is the
 *   row's badge: typed (`new`), taken from a source (`source`), prefilled from a broker file (`file`).
 * - **Rows**: the table shows the «dry» voices (a number, a percentage, an amount, a date, a choice, a country, a
 *   currency, a text); maps (sectors, countries) have a panel, the coupon schedule its own. A row keeps what the user
 *   typed; a percentage is typed in percent («0,20») and stored as a fraction («0.002»), exactly, on decimal text —
 *   never floats, which the catalogue refuses.
 * - **Light checks** only: no voice, the same voice twice, an empty value without «Lascia vuoto», a text that is not a
 *   number or a date. Signs, choices and sums are the backend's (`POST /assets/validate`).
 * - **The comparison after «Chiedi»**, as `assetMetadataComparison.ts` does for the asset: the baseline of a voice is its
 *   pending change, else «Adesso»; empty → filled from the source; equal (numerically, maps in any key order) → nothing;
 *   different → a difference to choose. A voice asked that no source gives is «no data», or «no answer» when a source
 *   failed (an error, refused for too many requests).
 *
 * @module features/assets/profile/profileEditState
 */
import {canonicalDecimal, canonicalInput, compareDecimal, fractionToPercent, percentToFraction} from '$lib/utils/core/exactDecimal';
import type {ProfileVoice} from './profileStore';

// =============================================================================
// Types
// =============================================================================

/** Where a change came from: typed by the user, taken from a source, prefilled from a broker file. */
export type ChangeOrigin = 'new' | 'source' | 'file';

/** One pending change of a voice. `value` is the catalogue's stored form; `source`/`seen` only for `kind: 'source'`. */
export interface PendingVoice {
    key: string;
    kind: 'value' | 'emptied' | 'source';
    value?: unknown;
    source?: string;
    seen?: unknown;
    origin: ChangeOrigin;
}

/** The pending changes of the window, by voice. */
export type PendingChanges = Record<string, PendingVoice>;

/** An amount as its cell edits it: decimal text and a currency code. */
export interface AmountInput {
    amount: string | null;
    currency: string | null;
}

/** A row of the table: what the user typed for one voice. */
export interface EditRow {
    id: string;
    /** The voice; null while the user has not chosen one. */
    key: string | null;
    /** The typed value (a percentage in percent; a date ISO; a code; a text). Unused by an amount. */
    input: string;
    /** The amount of an amount voice. */
    amount: AmountInput | null;
    /** «Lascia vuoto»: an empty value written on purpose. */
    emptied: boolean;
    origin: ChangeOrigin;
    /** The change the row was built from (a source's or a file's value): unchanged, it is handed back as it was. */
    base: {pending: PendingVoice; input: string; amount: AmountInput | null} | null;
}

/** What is wrong with a row. */
export type RowIssue = 'no_voice' | 'duplicate' | 'empty' | 'not_a_number' | 'not_a_date';

/** Where a voice is edited: a row of the table, a panel (a map), the coupon schedule's own panel. */
export type VoicePlace = 'row' | 'panel' | 'table';

/** «Adesso»: the value a voice has now, and who gave it. */
export interface CurrentVoice {
    value: unknown;
    source: string;
}

/** A difference between the baseline of a voice and what a source gives: one card of the comparison window. */
export interface ProfileDifference {
    key: string;
    current: unknown;
    proposed: unknown;
    source: string;
}

/** The answer of `POST /assets/profile/ask`, as much as the comparison reads. */
export interface AskAnswer {
    voices: Record<string, {value?: unknown; source: string}>;
    outcomes: Array<{code: string; status: string; error_code?: string | null}>;
}

/** What a «Chiedi» does to the window. */
export interface AskComparison {
    /** Empty voices filled from a source («dalla fonte»). */
    fills: PendingVoice[];
    /** Voices equal to the source: nothing to show. */
    equal: string[];
    /** Voices that differ: the cards of the comparison window. */
    differences: ProfileDifference[];
    /** Voices asked that no source gives. */
    missing: string[];
    /** Voices asked that no source could answer for (a source failed). */
    unanswered: string[];
}

// =============================================================================
// Voices, rows, pending changes
// =============================================================================

/** Where a voice is edited. */
export function voicePlace(voice: ProfileVoice): VoicePlace {
    if (voice.shape === 'map') return 'panel';
    if (voice.shape === 'table') return 'table';
    return 'row';
}

/** A new row typed by the user. */
export function newRow(id: string, key: string | null, input: string): EditRow {
    return {id, key, input, amount: null, emptied: false, origin: 'new', base: null};
}

function asText(value: unknown): string {
    return value === null || value === undefined ? '' : String(value);
}

/** A row that shows a pending change (its stored value back in the form the user types: a percentage in percent). */
export function rowFromPending(pending: PendingVoice, voice: ProfileVoice, id: string = pending.key): EditRow {
    let input = '';
    let amount: AmountInput | null = null;
    if (pending.kind !== 'emptied') {
        if (voice.shape === 'amount') {
            const stored = (pending.value ?? {}) as {amount?: unknown; currency?: unknown};
            amount = {amount: stored.amount === undefined ? null : asText(stored.amount), currency: stored.currency === undefined ? null : asText(stored.currency)};
        } else if (voice.shape === 'percentage') {
            input = fractionToPercent(asText(pending.value)) ?? asText(pending.value);
        } else {
            input = asText(pending.value);
        }
    }
    return {id, key: pending.key, input, amount, emptied: pending.kind === 'emptied', origin: pending.origin, base: {pending, input, amount}};
}

function sameAmount(left: AmountInput | null, right: AmountInput | null): boolean {
    return (left?.amount ?? null) === (right?.amount ?? null) && (left?.currency ?? null) === (right?.currency ?? null);
}

/** The stored form of what a row holds, or null when it holds nothing valid. */
function storedValue(row: EditRow, voice: ProfileVoice): unknown | null {
    switch (voice.shape) {
        case 'percentage': {
            const canonical = canonicalInput(row.input);
            return canonical === null ? null : percentToFraction(canonical);
        }
        case 'number':
            return canonicalInput(row.input);
        case 'amount': {
            const amount = canonicalInput(row.amount?.amount ?? null);
            const currency = (row.amount?.currency ?? '').trim();
            return amount === null || currency === '' ? null : {amount, currency};
        }
        case 'date':
            return ISO_DATE.test(row.input.trim()) ? row.input.trim() : null;
        default: {
            const text = row.input.trim();
            return text === '' ? null : text;
        }
    }
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

/** The pending change a row stands for, or null while it has an issue. */
export function pendingFromRow(row: EditRow, voice: ProfileVoice): PendingVoice | null {
    if (!row.key) return null;
    const unchanged = row.base !== null && row.base.pending.key === row.key && row.emptied === (row.base.pending.kind === 'emptied') && row.input === row.base.input && sameAmount(row.amount, row.base.amount);
    if (unchanged && row.base) return row.base.pending;
    if (row.emptied) return {key: row.key, kind: 'emptied', origin: 'new'};
    const value = storedValue(row, voice);
    if (value === null) return null;
    return {key: row.key, kind: 'value', value, origin: 'new'};
}

/** What is wrong with each row (rows without an issue are absent). Checks only what the window can tell alone. */
export function rowIssues(rows: EditRow[], voices: Map<string, ProfileVoice>): Record<string, RowIssue> {
    const issues: Record<string, RowIssue> = {};
    const counts = new Map<string, number>();
    for (const row of rows) if (row.key) counts.set(row.key, (counts.get(row.key) ?? 0) + 1);
    for (const row of rows) {
        const voice = row.key ? voices.get(row.key) : undefined;
        if (!row.key || !voice) issues[row.id] = 'no_voice';
        else if ((counts.get(row.key) ?? 0) > 1) issues[row.id] = 'duplicate';
        else if (row.emptied) continue;
        else {
            const issue = valueIssue(row, voice);
            if (issue) issues[row.id] = issue;
        }
    }
    return issues;
}

function valueIssue(row: EditRow, voice: ProfileVoice): RowIssue | null {
    if (voice.shape === 'amount') {
        const amount = (row.amount?.amount ?? '').trim();
        if (amount === '' || !(row.amount?.currency ?? '').trim()) return 'empty';
        return canonicalInput(amount) === null ? 'not_a_number' : null;
    }
    const text = row.input.trim();
    if (text === '') return 'empty';
    if ((voice.shape === 'number' || voice.shape === 'percentage') && canonicalInput(text) === null) return 'not_a_number';
    if (voice.shape === 'date' && !ISO_DATE.test(text)) return 'not_a_date';
    return null;
}

// =============================================================================
// Panels (maps)
// =============================================================================

/** A panel's weights (fractions, as `DistributionEditor` gives them) as a pending change in decimal text. */
export function pendingFromPanel(key: string, weights: Record<string, number>, origin: ChangeOrigin): PendingVoice {
    const value = Object.fromEntries(Object.entries(weights).map(([name, weight]) => [name, canonicalDecimal(weight.toFixed(4)) ?? '0']));
    return {key, kind: 'value', value, origin};
}

/**
 * The panels' changes after the user edited the panel of `key` (E9b). Weights are a value. An empty panel is never sent
 * as an empty map, which the backend refuses: over a map «Adesso» holds it empties the voice on purpose (null), over
 * none it is no change, and a change waiting there is taken back.
 */
export function withPanel(changes: PendingChanges, key: string, weights: Record<string, number>, current: Record<string, CurrentVoice>): PendingChanges {
    if (Object.keys(weights).length > 0) return {...changes, [key]: pendingFromPanel(key, weights, 'new')};
    const {[key]: _taken, ...others} = changes;
    const stored = panelWeights(current[key]?.value);
    return stored && Object.keys(stored).length > 0 ? {...others, [key]: {key, kind: 'emptied', origin: 'new'}} : others;
}

/** A stored map (decimal text) as the numbers a panel edits; null for none. */
export function panelWeights(stored: unknown): Record<string, number> | null {
    if (!stored || typeof stored !== 'object') return null;
    return Object.fromEntries(Object.entries(stored as Record<string, unknown>).map(([name, weight]) => [name, Number(weight)]));
}

// =============================================================================
// PATCH /assets
// =============================================================================

/** The `profile` of `PATCH /assets`: a value, null for «Lascia vuoto», `{from, seen}` for a source's value. */
export function profilePatch(pending: PendingChanges): Record<string, unknown> {
    return Object.fromEntries(
        Object.values(pending).map((change) => {
            if (change.kind === 'emptied') return [change.key, null];
            if (change.kind === 'source') return [change.key, {from: change.source, seen: change.seen}];
            return [change.key, change.value];
        }),
    );
}

// =============================================================================
// «Chiedi»
// =============================================================================

function isEmpty(value: unknown): boolean {
    return value === null || value === undefined || value === '';
}

/** Two stored values are the same: numbers by value, amounts by amount and currency, maps in any key order. */
export function sameStoredValue(left: unknown, right: unknown): boolean {
    if (typeof left === 'string' && typeof right === 'string') {
        if (canonicalDecimal(left) !== null && canonicalDecimal(right) !== null) return compareDecimal(left, right) === 0;
        return left === right;
    }
    if (Array.isArray(left) || Array.isArray(right)) return JSON.stringify(left) === JSON.stringify(right);
    if (left && right && typeof left === 'object' && typeof right === 'object') {
        const leftKeys = Object.keys(left as object).sort();
        const rightKeys = Object.keys(right as object).sort();
        if (leftKeys.join('\u0000') !== rightKeys.join('\u0000')) return false;
        return leftKeys.every((key) => sameStoredValue((left as Record<string, unknown>)[key], (right as Record<string, unknown>)[key]));
    }
    return left === right;
}

/** The baseline a source's value is compared with: the pending change (emptied → empty), else «Adesso». */
function baseline(key: string, pending: PendingChanges, current: Record<string, CurrentVoice>): unknown {
    const change = pending[key];
    if (change) return change.kind === 'emptied' ? null : change.value;
    return current[key]?.value ?? null;
}

/**
 * What a «Chiedi» does: `keys` are the voices asked (a row, a panel), null for «Chiedi tutto» (every voice a source
 * gave, also those not in the table yet).
 */
export function compareAsk(answer: AskAnswer, context: {keys: string[] | null; pending: PendingChanges; current: Record<string, CurrentVoice>}): AskComparison {
    const result: AskComparison = {fills: [], equal: [], differences: [], missing: [], unanswered: []};
    const someSourceFailed = answer.outcomes.some((outcome) => outcome.status !== 'ok' && outcome.status !== 'not_found');
    for (const key of context.keys ?? Object.keys(answer.voices)) {
        const given = answer.voices[key];
        if (!given || isEmpty(given.value)) {
            (someSourceFailed ? result.unanswered : result.missing).push(key);
            continue;
        }
        const base = baseline(key, context.pending, context.current);
        if (isEmpty(base)) result.fills.push({key, kind: 'source', value: given.value, source: given.source, seen: given.value, origin: 'source'});
        else if (sameStoredValue(base, given.value)) result.equal.push(key);
        else result.differences.push({key, current: base, proposed: given.value, source: given.source});
    }
    return result;
}

/** The pending changes once the differences chosen in the comparison window are taken «dalla fonte». */
export function applyDifferences(pending: PendingChanges, differences: ProfileDifference[], chosen: string[]): PendingChanges {
    const next = {...pending};
    for (const difference of differences) {
        if (!chosen.includes(difference.key)) continue;
        next[difference.key] = {key: difference.key, kind: 'source', value: difference.proposed, source: difference.source, seen: difference.proposed, origin: 'source'};
    }
    return next;
}
