/**
 * enrichersEditState — the logic of the «Arricchitori dell'asset» window (plan 68, E7), as pure functions: the window
 * keeps the DOM, the searches and the tests; this module decides.
 *
 * - **The draft** is the list the user is shaping: the codes chosen in their order (the priority), the binding of each,
 *   and the bindings of the ones removed, so a row put back comes back as it was. `resultConfig` is what the window
 *   hands back to the asset window, which saves it with the asset (`enrichers` of `PATCH /assets`, of a create item):
 *   an untouched window hands back the same object, keys, order and the plugin's free parameters.
 * - **A binding to an enricher the instance does not serve** (turned off by `LIBREFOLIO_ENRICHERS_ENABLED`, or no
 *   longer installed: its code is not in the catalogue) stays in its place, drawn off, and is kept at the save: turning
 *   it off is the instance's choice, not the user's order (plan B2). One not configured is drawn off with «Configure».
 * - **«Non in elenco»** holds every other enricher of the catalogue, with its reason.
 * - **The last read** of a row comes from the asset's `state`, by code: a row removed and put back finds its own.
 * - **What an enricher fills** is said in topics («costi, struttura, paesi, settori»): each voice of the catalogue
 *   declares its topic, and the backend's order of the topics is the order shown (`topicsOf`, E7b).
 *
 * @module features/assets/enrichers/enrichersEditState
 */
import type {z} from 'zod';
import {schemas} from '$lib/api/generated';
import type {ProfileVoice} from '$lib/features/assets/profile/profileStore';

// =============================================================================
// Types
// =============================================================================

/** One enricher of `GET /assets/enrichers`. */
export type EnricherInfo = z.infer<typeof schemas.FAEnricherInfo>;
/** What «Riconosci» or «Testa» found for one enricher. */
export type EnricherRecognition = z.infer<typeof schemas.FAEnricherRecognition>;

/** How one enricher names the asset: the two fields every binding holds, and the plugin's own parameters beside them. */
export interface EnricherBinding {
    identifier_type: string;
    identifier: string;
    [param: string]: unknown;
}

/** An asset's `enrichers.state` entry: the last read of one enricher. */
export interface EnricherReadState {
    read_at?: string | null;
    status?: string | null;
    error_code?: string | null;
    [field: string]: unknown;
}

/** The list being shaped in the window. */
export interface EnrichersDraft {
    /** The codes chosen, in their order (the first wins a voice). */
    order: string[];
    /** The binding of every code the window knows: the chosen ones and the ones removed. */
    bindings: Record<string, EnricherBinding>;
}

/** What the rows are drawn against. */
export interface EnrichersContext {
    catalogue: EnricherInfo[];
    /** The asset's type (`ETF`, `BOND`…): what each enricher covers and fills depends on it. */
    assetType: string;
    /** The asset's `enrichers.state` (empty for an asset not created yet). */
    state: Record<string, EnricherReadState>;
    /** What «Riconosci» found, by code (E8 hands it over). */
    recognitions: Record<string, EnricherRecognition>;
    /** The codes «Riconosci» is still asking. */
    searching: string[];
    /** The tickers a found one may enter by (ENR-2): the price assignment's symbol; any other ticker is the asset's own,
     *  bare, and never enters by itself (R2, R6). */
    trustedTickers?: string[];
}

/** Whether the instance can use a chosen enricher. */
/**
 * The line under the asset window's header: what «Riconosci» found (`state`, `text`) and, once it found some, what the
 * automatic «Chiedi» is doing with them (`reading`: asking now, or waiting out a 429; plan 68 E9b2).
 */
export interface EnrichersBanner {
    state: 'running' | 'found' | 'none' | 'refused' | 'error';
    text: string;
    reading: 'running' | 'waiting' | 'none';
    readingText: string | null;
}

export type Availability = 'ok' | 'not_configured' | 'off';

/** What is wrong with a binding. */
export type BindingIssue = 'no_identifier' | 'type_not_accepted';

/** The last read of a row: its day (UTC, `yyyy-mm-dd`) and outcome. */
export interface LastRead {
    day: string;
    status: string;
    errorCode: string | null;
}

/** A row of the chosen enrichers. */
export interface ChosenRow {
    code: string;
    /** 1-based: the priority shown as «#1». */
    position: number;
    binding: EnricherBinding;
    /** The catalogue's entry; null when the instance does not serve it. */
    info: EnricherInfo | null;
    availability: Availability;
    /** The settings to set, for a not configured one. */
    missing: string[];
    lastRead: LastRead | null;
    /** The voices it can fill for this asset type. */
    fills: string[];
    /** The name a recognition found. */
    foundName: string | null;
    pageUrl: string | null;
    issue: BindingIssue | null;
    /** «Riconosci» found nothing with the binding the row still holds (R3): the row says so, to correct or search. */
    notFoundWith: {identifier_type: string; identifier: string} | null;
    /** «Riconosci» found, with the binding the row still holds, an asset naming another identifier (B4): the problem
     *  stays after the addition, so the row keeps saying so. The type → value the source named. */
    conflictWith: Record<string, string> | null;
}

/** Why an enricher is not in the list, in the order «Non in elenco» shows them. */
export const OTHER_REASONS = ['removed', 'found', 'new', 'searching', 'not_found', 'conflict', 'error', 'not_configured', 'not_covering'] as const;
export type OtherReason = (typeof OTHER_REASONS)[number];

/** A row of «Non in elenco». */
export interface OtherRow {
    code: string;
    info: EnricherInfo;
    reason: OtherReason;
    /** The binding it would be added with: a removed one's, a found one's; null when it needs one typed. */
    binding: EnricherBinding | null;
    recognition: EnricherRecognition | null;
    fills: string[];
    /** It can be added: not one that does not cover the type, nor one not configured, nor one «Riconosci» is still asking. */
    canAdd: boolean;
    /** Found only by a ticker (R2): it never enters by itself, the user reads its name and adds it. */
    tickerOnly: boolean;
}

// =============================================================================
// The draft
// =============================================================================

/** The draft of an asset's config (`enrichers.config`): its codes in order, their bindings as they are. */
export function draftFrom(config: Record<string, EnricherBinding>): EnrichersDraft {
    return {order: Object.keys(config), bindings: {...config}};
}

/** What the window hands back: the chosen codes in their order, each with its binding. */
export function resultConfig(draft: EnrichersDraft): Record<string, EnricherBinding> {
    return Object.fromEntries(draft.order.map((code) => [code, draft.bindings[code]]));
}

/** The draft differs from the config it was opened with: another order, another code, another binding. */
export function isChanged(draft: EnrichersDraft, config: Record<string, EnricherBinding>): boolean {
    return JSON.stringify(Object.entries(resultConfig(draft))) !== JSON.stringify(Object.entries(config));
}

/** Remove a chosen enricher: its binding stays known, to come back as it was. */
export function removeEnricher(draft: EnrichersDraft, code: string): EnrichersDraft {
    return {...draft, order: draft.order.filter((candidate) => candidate !== code)};
}

/** What the asset already knows, for an enricher added by hand (R3): the types it accepts and the asset's identifiers. */
export interface AddFrom {
    /** The identifier types the enricher accepts, in the order its plugin declares them. */
    accepted?: string[];
    /** The asset's identifiers, type → value. */
    identifiers?: Record<string, string>;
}

/**
 * Put an enricher in the list, at the end (R3, «usa i dati che hai»): with the binding it had (removed and put back),
 * else the one a recognition asked with (found, or not found with X: the row then says so), else the first identifier
 * of the asset of a type it accepts, in the order its plugin declares them (ESMA ← the asset's ISIN), else one to
 * type, already on the first type it accepts.
 */
export function addEnricher(draft: EnrichersDraft, code: string, recognition?: EnricherRecognition | null, from: AddFrom = {}): EnrichersDraft {
    if (draft.order.includes(code)) return draft;
    const binding = draft.bindings[code] ?? (recognition ? recognitionBinding(recognition) : assetBinding(from));
    return {order: [...draft.order, code], bindings: {...draft.bindings, [code]: binding}};
}

/** The binding the asset's identifiers give an enricher: the first type it accepts that the asset holds, else empty. */
export function assetBinding(from: AddFrom): EnricherBinding {
    const accepted = from.accepted ?? [];
    const known = accepted.find((type) => (from.identifiers?.[type] ?? '').trim() !== '');
    return known ? {identifier_type: known, identifier: (from.identifiers?.[known] ?? '').trim()} : {identifier_type: accepted[0] ?? '', identifier: ''};
}

/**
 * «Riconosci»'s proposal taken into the window's draft (R2), while the user has not touched the list: the found ones,
 * in the proposal's order (the order of arrival, then `default_order`). It never reaches the asset by itself: it is
 * saved only with «Usa questi arricchitori» and «Salva Modifiche» (K2). Once the user touched the list the window stops
 * calling this: what is found later waits in «Non in elenco».
 */
export function adoptProposal(draft: EnrichersDraft, proposal: Record<string, EnricherBinding>): EnrichersDraft {
    return {order: Object.keys(proposal), bindings: {...draft.bindings, ...proposal}};
}

/**
 * A found enricher that enters the list by itself: not one found by a ticker (R2, another listing is possible), unless
 * that ticker is one of `trustedTickers`, the price assignment's symbol (ENR-2, R6: `SWDA.MI`, the listing the asset is
 * priced on).
 */
export function entersAlone(recognition: EnricherRecognition | null | undefined, trustedTickers: readonly string[] = []): boolean {
    if (recognition?.status !== 'found') return false;
    return recognition.identifier_type !== 'TICKER' || trustedTickers.includes(recognition.identifier);
}

/** A new order: the codes given that are chosen, then the chosen ones it did not name, in their order. */
export function reorder(draft: EnrichersDraft, codes: string[]): EnrichersDraft {
    const named = codes.filter((code, index) => draft.order.includes(code) && codes.indexOf(code) === index);
    return {...draft, order: [...named, ...draft.order.filter((code) => !named.includes(code))]};
}

/** Change the binding of an enricher. */
export function setBinding(draft: EnrichersDraft, code: string, binding: EnricherBinding): EnrichersDraft {
    return {...draft, bindings: {...draft.bindings, [code]: binding}};
}

// =============================================================================
// Bindings
// =============================================================================

/** The binding a recognition answered for: its type and identifier, and its parameters (a seed's, ENR-2). */
export function recognitionBinding(recognition: EnricherRecognition): EnricherBinding {
    return {...((recognition.params as Record<string, unknown> | undefined) ?? {}), identifier_type: recognition.identifier_type, identifier: recognition.identifier};
}

/** A search result or a recognition chosen: its type and identifier, the binding's parameters kept. */
export function bindingFromResult(binding: EnricherBinding, result: {identifier_type: string; identifier: string}): EnricherBinding {
    return {...binding, identifier_type: result.identifier_type, identifier: result.identifier};
}

/** The binding with the parameters of the plugin's form: an empty value is not sent (the plugin reads «absent»). */
export function withParams(binding: EnricherBinding, params: Record<string, unknown>): EnricherBinding {
    const next: EnricherBinding = {...binding};
    for (const [key, value] of Object.entries(params)) {
        if (key === 'identifier_type' || key === 'identifier') continue;
        const text = typeof value === 'string' ? value.trim() : value;
        if (text === '' || text === null || text === undefined) delete next[key];
        else next[key] = text;
    }
    return next;
}

/** What is wrong with a binding: no identifier, a type the enricher does not accept (unknown when it is not served). */
export function bindingIssue(binding: EnricherBinding, info: EnricherInfo | null): BindingIssue | null {
    if (!binding.identifier?.trim() || !binding.identifier_type?.trim()) return 'no_identifier';
    if (info && !info.accepted_identifier_types.includes(binding.identifier_type)) return 'type_not_accepted';
    return null;
}

/** The issues of the chosen rows the instance can use, by code (a binding to an enricher it does not serve is kept as it is). */
export function draftIssues(draft: EnrichersDraft, context: EnrichersContext): Record<string, BindingIssue> {
    return Object.fromEntries(
        chosenRows(draft, context)
            .filter((row) => row.issue !== null)
            .map((row) => [row.code, row.issue as BindingIssue]),
    );
}

// =============================================================================
// Rows
// =============================================================================

function lastRead(entry: EnricherReadState | undefined): LastRead | null {
    if (!entry || !entry.read_at || !entry.status) return null;
    return {day: String(entry.read_at).slice(0, 10), status: String(entry.status), errorCode: entry.error_code ?? null};
}

/**
 * The last read of an asset (E6c, the hint of «Aggiorna»): the latest day an enricher still bound was read, whatever the
 * outcome; `state` keeps the reads of enrichers removed since (B3), which do not count. `null`: never read.
 */
export function assetLastRead(config: Record<string, unknown>, state: Record<string, EnricherReadState>): string | null {
    const days = Object.keys(config)
        .map((code) => lastRead(state[code])?.day ?? null)
        .filter((day): day is string => day !== null);
    return days.length ? days.reduce((latest, day) => (day > latest ? day : latest)) : null;
}

function fillsOf(info: EnricherInfo | null | undefined, assetType: string): string[] {
    return [...((info?.voices as Record<string, string[]> | undefined)?.[assetType] ?? [])];
}

/** The chosen enrichers, in their order. */
export function chosenRows(draft: EnrichersDraft, context: EnrichersContext): ChosenRow[] {
    const byCode = new Map(context.catalogue.map((entry) => [entry.code, entry]));
    return draft.order.map((code, index) => {
        const info = byCode.get(code) ?? null;
        const binding = draft.bindings[code];
        const availability: Availability = info === null ? 'off' : info.configured === false ? 'not_configured' : 'ok';
        const recognition = context.recognitions[code];
        return {
            code,
            position: index + 1,
            binding,
            info,
            availability,
            missing: info?.missing_settings ? [...info.missing_settings] : [],
            lastRead: lastRead(context.state[code]),
            fills: fillsOf(info, context.assetType),
            foundName: recognition?.status === 'found' ? (recognition.name ?? null) : null,
            pageUrl: recognition?.page_url ?? null,
            issue: availability === 'off' ? null : bindingIssue(binding, info),
            notFoundWith: recognition?.status === 'not_found' && binding?.identifier_type === recognition.identifier_type && binding?.identifier === recognition.identifier ? {identifier_type: recognition.identifier_type, identifier: recognition.identifier} : null,
            conflictWith: recognition?.status === 'conflict' && binding?.identifier_type === recognition.identifier_type && binding?.identifier === recognition.identifier && Object.keys(recognition.conflicts ?? {}).length ? {...recognition.conflicts} : null,
        };
    });
}

function otherReason(code: string, info: EnricherInfo, draft: EnrichersDraft, context: EnrichersContext): OtherReason {
    if (code in draft.bindings) return 'removed';
    if ((info.default_priority as Record<string, number | null | undefined>)[context.assetType] == null) return 'not_covering';
    if (info.configured === false) return 'not_configured';
    if (context.searching.includes(code)) return 'searching';
    const status = context.recognitions[code]?.status;
    if (status === 'found' || status === 'not_found' || status === 'conflict' || status === 'error') return status;
    return 'new';
}

/** «Non in elenco»: every enricher of the catalogue not chosen, with its reason, in the order of `OTHER_REASONS`. */
export function otherRows(draft: EnrichersDraft, context: EnrichersContext): OtherRow[] {
    const rows = context.catalogue
        .filter((info) => !draft.order.includes(info.code))
        .map((info): OtherRow => {
            const reason = otherReason(info.code, info, draft, context);
            const recognition = context.recognitions[info.code] ?? null;
            const binding = reason === 'removed' ? draft.bindings[info.code] : reason === 'found' && recognition ? recognitionBinding(recognition) : null;
            return {
                code: info.code,
                info,
                reason,
                binding,
                recognition,
                fills: fillsOf(info, context.assetType),
                canAdd: reason !== 'not_covering' && reason !== 'not_configured' && reason !== 'searching',
                tickerOnly: reason === 'found' && !entersAlone(recognition, context.trustedTickers),
            };
        });
    return rows.sort((left, right) => OTHER_REASONS.indexOf(left.reason) - OTHER_REASONS.indexOf(right.reason));
}

// =============================================================================
// The line of «Riconosci» in the enrichers' window (ENR-1)
// =============================================================================

/** Where «Riconosci» stands, for the line on top of the enrichers' window. */
export type RecognitionLineState = 'running' | 'found' | 'none' | 'refused' | 'error' | 'no_identifiers';

export interface RecognitionLine {
    state: RecognitionLineState;
    /** The covering enrichers that answered, and how many there are (`running`). */
    answered: number;
    asked: number;
    /** The codes found, in the order of the catalogue (`found`). */
    found: string[];
}

/**
 * The line of «Riconosci» (R1): asking (how many answered), found (who), none, waiting out a refusal, failed; or nothing
 * to recognise with (`canAsk` false: no identifier any covering enricher accepts). `null` before it starts. `askable`
 * are the codes expected to answer (configured, accepting an identifier the asset holds): the cascade never answers
 * for the others, so «N of M» counts on these only; the found ones are any covering one.
 */
export function recognitionLine(status: 'idle' | 'running' | 'done' | 'refused' | 'error', recognitions: Record<string, EnricherRecognition>, covering: string[], canAsk: boolean, askable: string[] = covering): RecognitionLine | null {
    const answered = askable.filter((code) => code in recognitions).length;
    const found = covering.filter((code) => recognitions[code]?.status === 'found');
    const line = (state: RecognitionLineState): RecognitionLine => ({state, answered, asked: askable.length, found});
    if (status === 'running') return line('running');
    if (status === 'refused') return line('refused');
    if (status === 'error') return line('error');
    if (status === 'done') return line(found.length ? 'found' : 'none');
    return canAsk ? null : line('no_identifiers');
}

// =============================================================================
// What an enricher fills, in topics
// =============================================================================

/** The order the topics are shown in: the backend's (`ProfileTopic`), never a second list here. */
const TOPIC_ORDER: readonly string[] = schemas.ProfileTopic.options;

/** The topics of the voices an enricher fills: each once, in `TOPIC_ORDER`, at most `max`, and how many more. */
export function topicsOf(voiceKeys: string[], catalogue: Pick<ProfileVoice, 'key' | 'topic'>[], max = 4): {topics: string[]; more: number} {
    const topicOf = new Map(catalogue.map((voice) => [voice.key, voice.topic as string]));
    const found = new Set(voiceKeys.map((key) => topicOf.get(key)).filter((topic): topic is string => topic !== undefined));
    const ordered = TOPIC_ORDER.filter((topic) => found.has(topic));
    return {topics: ordered.slice(0, max), more: Math.max(0, ordered.length - max)};
}
