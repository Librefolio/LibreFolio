/**
 * assetProfileDraft — the profile's pending changes as the asset window holds them (plan 68, E8b), as pure functions.
 *
 * The asset window keeps the changes the «Dati del profilo» window hands back («Tieni le modifiche» does not save) and
 * sends them with «Crea Asset» or «Salva Modifiche» (`profilePatch`). At creation, once the enrichers are settled, an
 * automatic «Chiedi» reads them and fills the empty voices «dalla fonte» (PROF §14.8). This module decides:
 *
 * - **the row**: how many changes wait, and which voices, in the catalogue's order (the fills count: they leave with
 *   the asset as the others do);
 * - **when the automatic «Chiedi» starts**: at creation only, with a list the user applied or «Riconosci» done — never on
 *   the proposal still growing, which would ask once per answer, each question a hit of the per-user limit;
 * - **what its answer does**: it fills the empty voices only; a voice the user wrote always wins, a difference is dropped
 *   (the comparison window is the user's own «Chiedi»); a later answer replaces the fills the user did not touch;
 * - **a fill whose source left the list** is dropped: the creation would refuse the whole asset;
 * - **the user's own changes** (the automatic fills untouched are not: they must not ask to discard anything);
 * - **whether the changes block the save**: a value the window would refuse (a broker file's prefill can be wrong);
 * - **«Adesso» in edit mode**: each voice's value today and who gave it, from a one-day read of the profile.
 * - **the description field** of the asset window (E9): a view of the profile's `description`, the waiting value else
 *   «Adesso»'s; what the user types there is a pending change like the window's own.
 *
 * @module features/assets/profile/assetProfileDraft
 */
import type {EnricherBinding} from '../enrichers/enrichersEditState';
import {compareAsk, rowFromPending, rowIssues, voicePlace, type AskAnswer, type CurrentVoice, type PendingChanges, type PendingVoice} from './profileEditState';
import type {ProfileVoice, ProfileVoices} from './profileStore';

/** What the «Dati del profilo» row shows: how many changes wait, and their voices in the catalogue's order. */
export function profileRowSummary(pending: PendingChanges, catalogue: readonly ProfileVoice[]): {count: number; keys: string[]} {
    const order = new Map(catalogue.map((voice, index) => [voice.key, index]));
    const keys = Object.keys(pending).sort((left, right) => (order.get(left) ?? Number.MAX_SAFE_INTEGER) - (order.get(right) ?? Number.MAX_SAFE_INTEGER));
    return {count: keys.length, keys};
}

/** The body of the automatic «Chiedi»: an asset not created yet, by its type and its enrichers. */
export interface AutoAskRequest {
    asset_type: string;
    enrichers: Record<string, EnricherBinding>;
}

/** The request of the automatic «Chiedi», or null when it must not start. */
export function autoAskRequest(context: {editMode: boolean; tourPreview: boolean; assetType: string; enrichers: Record<string, EnricherBinding>; settled: boolean}): AutoAskRequest | null {
    if (context.editMode || context.tourPreview || !context.settled || !context.assetType || Object.keys(context.enrichers).length === 0) return null;
    return {asset_type: context.assetType, enrichers: context.enrichers};
}

/** The identity of a question: the type and the list, in its order (the order is the priority). */
export function autoAskKey(request: AutoAskRequest): string {
    return JSON.stringify([request.asset_type, Object.entries(request.enrichers)]);
}

function samePending(left: PendingVoice | undefined, right: PendingVoice | undefined): boolean {
    return JSON.stringify(left ?? null) === JSON.stringify(right ?? null);
}

/**
 * The pending changes after an automatic «Chiedi»: the previous fills the user did not touch are taken back, then the
 * empty voices are filled from the answer; nothing else changes. `auto` is the fills now in place.
 */
export function mergeAutoFills(pending: PendingChanges, previousAuto: Record<string, PendingVoice>, answer: AskAnswer, current: Record<string, CurrentVoice>): {pending: PendingChanges; auto: Record<string, PendingVoice>} {
    const kept: PendingChanges = {};
    for (const [key, change] of Object.entries(pending)) if (!samePending(change, previousAuto[key])) kept[key] = change;
    const {fills} = compareAsk(answer, {keys: null, pending: kept, current});
    const auto = Object.fromEntries(fills.map((change) => [change.key, change]));
    return {pending: {...kept, ...auto}, auto};
}

/** The pending changes without the fills of a source the list no longer holds. */
export function withoutFillsOutside(pending: PendingChanges, enrichers: Record<string, EnricherBinding>): PendingChanges {
    return Object.fromEntries(Object.entries(pending).filter(([, change]) => change.kind !== 'source' || (change.source !== undefined && change.source in enrichers)));
}

/** The changes that are the user's: the automatic fills left as they came are not. */
export function userChanges(pending: PendingChanges, auto: Record<string, PendingVoice>): PendingChanges {
    return Object.fromEntries(Object.entries(pending).filter(([key, change]) => !samePending(change, auto[key])));
}

/** Whether a pending change holds a value the window would refuse: then the asset window cannot save. */
export function profileBlocksSave(pending: PendingChanges, catalogue: readonly ProfileVoice[]): boolean {
    const voices = new Map(catalogue.map((voice) => [voice.key, voice]));
    const rows = Object.values(pending)
        .filter((change) => change.kind === 'value')
        .flatMap((change) => {
            const voice = voices.get(change.key);
            return voice && voicePlace(voice) === 'row' ? [rowFromPending(change, voice)] : [];
        });
    return Object.keys(rowIssues(rows, voices)).length > 0;
}

/**
 * «Adesso» of an asset that exists: each voice's value today and who gave it, from a one-day read of the profile
 * (`readAssetProfile(id, {start: today})`); the last step when the read holds several. A voice emptied on purpose is
 * `null`; a voice without a step is left out.
 */
export function currentFromRead(voices: ProfileVoices): Record<string, CurrentVoice> {
    const current: Record<string, CurrentVoice> = {};
    for (const [key, steps] of Object.entries(voices)) {
        const last = steps[steps.length - 1];
        if (last) current[key] = {value: last.value ?? null, source: last.source};
    }
    return current;
}

/** The text of a description value: a string as it is, anything else (null, absent) as nothing. */
function descriptionText(value: unknown): string {
    return typeof value === 'string' ? value : '';
}

/**
 * What the description field of the asset window shows (E9): the description waiting to be saved — the user's, a
 * source's fill, or nothing when it is emptied on purpose — else «Adesso»'s, else nothing.
 */
export function descriptionShown(pending: PendingChanges, current: Record<string, CurrentVoice>): string {
    const change = pending.description;
    if (change) return change.kind === 'emptied' ? '' : descriptionText(change.kind === 'source' ? change.seen : change.value);
    return descriptionText(current.description?.value);
}

/**
 * The pending changes after the user typed `text` in the description field (E9). The text equal to «Adesso»'s, exactly,
 * is no change: the waiting one is taken back. Exactly, because the field shows what waits: a blank typed after
 * «Adesso»'s value, before the next word, must stay. An empty text (blanks alone) is no change at creation and, over a
 * description that exists, empties it on purpose (the save sends null). Anything else is a value of the user's, which
 * replaces a source's fill.
 */
export function withDescription(pending: PendingChanges, current: Record<string, CurrentVoice>, text: string): PendingChanges {
    const {description: _previous, ...others} = pending;
    const now = descriptionText(current.description?.value);
    if (text === now) return others;
    if (text.trim() === '') return now === '' ? others : {...others, description: {key: 'description', kind: 'emptied', origin: 'new'}};
    return {...others, description: {key: 'description', kind: 'value', value: text, origin: 'new'}};
}
