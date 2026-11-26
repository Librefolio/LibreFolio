/**
 * profileChanges.ts — one change of the asset profile as the «Ultime variazioni» panel and the «Storia del dato» window
 * show it (plan 68, E6a; 87, A3): its kind, the value before, the value after, and a short note with what the two values
 * do not say («Corretto a mano», «Tornato al valore di justETF: il 2 novembre Anna l'aveva corretto a mano», «Dati del 30
 * settembre (prima, del 31 agosto)»). Until 87 the same facts were one sentence, too long for a description. The kind is
 * published on the row (`data-kind`), so the tests read it instead of a translated text.
 *
 * Plain module: the caller hands in its translation and formatters.
 */
import type {z} from 'zod';
import type {schemas} from '$lib/api';
import {compareDecimal} from '$lib/utils/core/exactDecimal';
import type {ProfileVoice} from './profileStore';

/** One change of the profile, as `POST /assets/profile/query` answers it with `changes`. */
export type ProfileChange = z.infer<typeof schemas.FAProfileChange>;

/** The kinds of a change: each one with something to add is a key under `assets.profile.changes.note`. */
export type ChangeKind = 'first' | 'firstByHand' | 'firstLegacy' | 'refilled' | 'emptied' | 'emptiedBySource' | 'byHand' | 'backFromHand' | 'newSourceDate' | 'up' | 'down' | 'changed';

const USER = 'user';
const LEGACY = 'legacy';
/** The shapes whose values go up or down. */
const ORDERED = new Set(['number', 'percentage']);

/** An optional text field of a change: the generated type also allows an array, which the server never sends. */
export function text(value: unknown): string | null {
    return typeof value === 'string' ? value : null;
}

/** Which kind a change is. */
export function changeKind(change: ProfileChange, voice: ProfileVoice | undefined): ChangeKind {
    if (change.value === null || change.value === undefined) return change.source === USER ? 'emptied' : 'emptiedBySource';
    if (!change.has_previous) {
        if (change.source === USER) return 'firstByHand';
        return change.source === LEGACY ? 'firstLegacy' : 'first';
    }
    // The voice was empty before: no «from» to name
    if (change.previous === null || change.previous === undefined) return change.source === USER ? 'firstByHand' : 'refilled';
    if (change.source === USER) return 'byHand';
    if (text(change.previous_source) === USER) return 'backFromHand';
    const sourceDate = text(change.source_date);
    const previousSourceDate = text(change.previous_source_date);
    if (voice?.shape === 'map' && sourceDate && previousSourceDate && sourceDate !== previousSourceDate) return 'newSourceDate';
    if (voice && ORDERED.has(voice.shape) && change.previous !== null && change.previous !== undefined) {
        const order = compareDecimal(String(change.value), String(change.previous));
        if (order === 1) return 'up';
        if (order === -1) return 'down';
    }
    return 'changed';
}

/** What `changeParts` needs from its caller: the translation with values, and the formatters of the page. */
export interface ChangePartsContext {
    translate: (key: string, values?: Record<string, string>) => string;
    /** A stored value as the profile writes it (`formatProfileValue`). */
    format: (voice: ProfileVoice, value: unknown) => string;
    /** A day as the profile writes it (`formatProfileDay`). */
    day: (iso: string) => string;
    /** A source's name: an enricher's declared name, the profile's words for `user` and `legacy`. */
    source: (code: string) => string;
}

/** A change as the table shows it: the value before and after («» when there is none), and a note the two values alone
 *  do not say («» for a value that simply moved or changed). */
export interface ChangeParts {
    kind: ChangeKind;
    before: string;
    after: string;
    note: string;
}

/** The kinds whose two values say it all: no note. */
const PLAIN = new Set<ChangeKind>(['up', 'down', 'changed']);

/** «Prima», «Dopo» and the note of one change (87, A3). */
export function changeParts(change: ProfileChange, voice: ProfileVoice | undefined, context: ChangePartsContext): ChangeParts {
    const kind = changeKind(change, voice);
    const show = (value: unknown) => (value === null || value === undefined ? '' : voice ? context.format(voice, value) : String(value));
    let values: Record<string, string> = {};
    if (kind === 'backFromHand') {
        const date = text(change.previous_read_on);
        values = {date: date ? context.day(date) : '', name: text(change.previous_user_name) ?? context.translate('assets.profile.changes.who.deletedUser'), source: context.source(change.source)};
    } else if (kind === 'newSourceDate') {
        values = {date: context.day(text(change.source_date) ?? ''), previousDate: context.day(text(change.previous_source_date) ?? '')};
    }
    return {kind, before: change.has_previous ? show(change.previous) : '', after: show(change.value), note: PLAIN.has(kind) ? '' : context.translate(`assets.profile.changes.note.${kind}`, values)};
}
