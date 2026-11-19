/**
 * profileChanges.ts — «Cosa è cambiato» of one change of the asset profile (plan 68, E6a), for the «Ultime variazioni»
 * panel and the «Storia del dato» window: which kind of sentence a change gets, and the values it names.
 *
 * The wording is the mock's (round 39, approved in round 41): «Primo valore letto: 3,52 %», «Salito da 3,40 % a
 * 3,61 %», «Corretto a mano: da 3,59 % a 3,40 %», «Tornato a 0,14 %: il 2 novembre Anna l'aveva corretto a mano a
 * 0,12 %, ma justETF dice 0,14 %», «Ora sono i dati del 30 settembre (prima, del 31 agosto)». The kind is published on
 * the row (`data-kind`), so the tests read it instead of a translated text.
 *
 * Plain module: the caller hands in its translation and formatters.
 */
import type {z} from 'zod';
import type {schemas} from '$lib/api';
import {compareDecimal} from '$lib/utils/core/exactDecimal';
import type {ProfileVoice} from './profileStore';

/** One change of the profile, as `POST /assets/profile/query` answers it with `changes`. */
export type ProfileChange = z.infer<typeof schemas.FAProfileChange>;

/** The kinds of «Cosa è cambiato»: each one is a key under `assets.profile.changes.what`. */
export type ChangeKind = 'first' | 'firstByHand' | 'firstLegacy' | 'refilled' | 'emptied' | 'emptiedBySource' | 'byHand' | 'backFromHand' | 'newSourceDate' | 'up' | 'down' | 'changed';

const USER = 'user';
const LEGACY = 'legacy';
/** The shapes whose values go up or down. */
const ORDERED = new Set(['number', 'percentage']);

/** An optional text field of a change: the generated type also allows an array, which the server never sends. */
export function text(value: unknown): string | null {
    return typeof value === 'string' ? value : null;
}

/** Which sentence a change gets. */
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

/** What `changeSentence` needs from its caller: the translation with values, and the formatters of the page. */
export interface ChangeSentenceContext {
    translate: (key: string, values?: Record<string, string>) => string;
    /** A stored value as the profile writes it (`formatProfileValue`). */
    format: (voice: ProfileVoice, value: unknown) => string;
    /** A day as the profile writes it (`formatProfileDay`). */
    day: (iso: string) => string;
    /** A source's name: an enricher's declared name, the profile's words for `user` and `legacy`. */
    source: (code: string) => string;
}

/** «Cosa è cambiato» of one change: its kind and its text. */
export function changeSentence(change: ProfileChange, voice: ProfileVoice | undefined, context: ChangeSentenceContext): {kind: ChangeKind; text: string} {
    const kind = changeKind(change, voice);
    // A value's own final full stop goes: the sentence ends with its own («…test.» never «…test..»)
    const show = (value: unknown) => (voice ? context.format(voice, value) : String(value ?? '')).replace(/\.\s*$/, '');
    const to = show(change.value);
    const from = show(change.previous);
    let values: Record<string, string>;
    switch (kind) {
        case 'backFromHand':
            values = {
                to,
                from,
                date: text(change.previous_read_on) ? context.day(text(change.previous_read_on) ?? '') : '',
                name: text(change.previous_user_name) ?? context.translate('assets.profile.changes.who.deletedUser'),
                source: context.source(change.source),
            };
            break;
        case 'newSourceDate':
            values = {date: context.day(text(change.source_date) ?? ''), previousDate: context.day(text(change.previous_source_date) ?? '')};
            break;
        case 'byHand':
        case 'up':
        case 'down':
        case 'changed':
            values = {from, to};
            break;
        case 'emptied':
        case 'emptiedBySource':
            values = {};
            break;
        default:
            values = {to};
    }
    return {kind, text: context.translate(`assets.profile.changes.what.${kind}`, values)};
}
