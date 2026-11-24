/**
 * recognizeStream — «Riconosci» as the backend streams it (plan 68, E8a): `POST /api/v1/assets/enrichers/recognize`
 * answers Server-Sent Events, one `data: {json}` each, with an `event` key — `enricher_result` (one enricher's answer),
 * `identifier_learned` (a strong identifier the cascade learned) and last `done` (`found_order`, `default_order`,
 * `identifiers`).
 *
 * The API client (Zodios, axios) reads a whole answer; a stream needs `fetch`, as `priceRefresh.ts` does for its own
 * route. The parser keeps the bytes of a character or a line split across two chunks until the rest arrives.
 *
 * Outcomes are typed: `done` (with the `done` event, or null for a stream that ended without one), `refused` (429, the
 * per-user limit of the probes, C0, with its wait), `aborted` (the caller stopped it). Any other failure throws.
 *
 * @module features/assets/enrichers/recognizeStream
 */
import type {EnricherRecognition} from './enrichersEditState';

export const RECOGNIZE_PATH = '/api/v1/assets/enrichers/recognize';

/** A binding to start from (ENR-2): the asset's price assignment, by the price provider's code. */
export interface RecognizeSeed {
    code: string;
    identifier_type: string;
    identifier: string;
    params?: Record<string, unknown>;
}

/** What «Riconosci» is asked: the asset's type, the identifiers known, its price provider (first at equal degree), and
 *  the bindings to start from. */
export interface RecognizeRequest {
    asset_type: string;
    identifiers: Record<string, string>;
    price_provider_code?: string | null;
    codes?: string[];
    seeds?: RecognizeSeed[];
}

export type EnricherResultEvent = {event: 'enricher_result'} & EnricherRecognition;
export interface IdentifierLearnedEvent {
    event: 'identifier_learned';
    identifier_type: string;
    identifier: string;
    source: string;
}
export interface RecognizeDoneEvent {
    event: 'done';
    found_order: string[];
    default_order: string[];
    identifiers: Record<string, string>;
}
export type RecognizeEvent = EnricherResultEvent | IdentifierLearnedEvent | RecognizeDoneEvent;

export type RecognizeOutcome = {kind: 'done'; done: RecognizeDoneEvent | null} | {kind: 'refused'; retryAfter: number | null} | {kind: 'aborted'};

/** A parser of a Server-Sent Events stream: bytes in, whole JSON events out. */
export function createSseParser<T = RecognizeEvent>(): {push: (chunk: Uint8Array) => T[]; end: () => T[]} {
    const decoder = new TextDecoder();
    let buffer = '';
    function events(): T[] {
        const out: T[] = [];
        let cut = buffer.indexOf('\n\n');
        while (cut >= 0) {
            const block = buffer.slice(0, cut);
            buffer = buffer.slice(cut + 2);
            const data = block
                .split('\n')
                .filter((line) => line.startsWith('data:'))
                .map((line) => line.slice(5).trimStart())
                .join('\n');
            if (data) {
                try {
                    out.push(JSON.parse(data) as T);
                } catch {
                    // Not an event: skipped
                }
            }
            cut = buffer.indexOf('\n\n');
        }
        return out;
    }
    return {
        push(chunk) {
            buffer += decoder.decode(chunk, {stream: true}).replace(/\r\n/g, '\n');
            return events();
        },
        end() {
            buffer += decoder.decode();
            if (buffer && !buffer.endsWith('\n\n')) buffer += '\n\n';
            return events();
        },
    };
}

export function isAbort(error: unknown, signal: AbortSignal | undefined): boolean {
    return signal?.aborted === true || (error instanceof DOMException && error.name === 'AbortError');
}

export async function retryAfterOf(response: Response): Promise<number | null> {
    try {
        const detail = ((await response.json()) as {detail?: {retry_after?: unknown}})?.detail;
        if (typeof detail?.retry_after === 'number') return detail.retry_after;
    } catch {
        // No JSON body: the header below
    }
    const header = Number(response.headers.get('Retry-After'));
    return Number.isFinite(header) && header > 0 ? header : null;
}

/** «Riconosci»: every event handed over as it arrives; the outcome when the stream ends. */
export async function recognizeEnrichers(request: RecognizeRequest, options: {onEvent: (event: RecognizeEvent) => void; signal?: AbortSignal; fetchImpl?: typeof fetch}): Promise<RecognizeOutcome> {
    const {onEvent, signal, fetchImpl = fetch} = options;
    let done: RecognizeDoneEvent | null = null;
    const hand = (list: RecognizeEvent[]) => {
        for (const event of list) {
            if (event.event === 'done') done = event;
            onEvent(event);
        }
    };
    try {
        const response = await fetchImpl(RECOGNIZE_PATH, {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', Accept: 'text/event-stream'}, body: JSON.stringify(request), signal});
        if (response.status === 429) return {kind: 'refused', retryAfter: await retryAfterOf(response)};
        if (!response.ok || !response.body) throw new Error(`recognize: HTTP ${response.status}`);
        const parser = createSseParser();
        const reader = response.body.getReader();
        for (;;) {
            const {value, done: finished} = await reader.read();
            if (finished) break;
            if (value) hand(parser.push(value));
        }
        hand(parser.end());
        return {kind: 'done', done};
    } catch (error) {
        if (isAbort(error, signal)) return {kind: 'aborted'};
        throw error;
    }
}
