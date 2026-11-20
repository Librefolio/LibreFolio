/**
 * recognizeStream (plan 68, E8a): «Riconosci» as the backend streams it (`POST /assets/enrichers/recognize`, Server-Sent
 * Events: `enricher_result`, `identifier_learned`, last `done`).
 *
 * Pinned:
 * - the parser hands over whole events only: a `data:` line split across two chunks, and a multi-byte character split
 *   across two chunks, arrive whole; two events in one chunk arrive as two; a line that is not JSON is skipped;
 * - the call posts the request as JSON with the session cookie, hands every event over as it arrives and answers the
 *   `done` event; a stream that ends without `done` answers null;
 * - a 429 is a typed refusal with its wait (`retry_after`), never a throw; another failure throws;
 * - an aborted call stops quietly.
 */
import {describe, expect, it, vi} from 'vitest';
import {createSseParser, recognizeEnrichers, RECOGNIZE_PATH, type RecognizeEvent} from './recognizeStream';

const encoder = new TextEncoder();

function streamOf(chunks: Uint8Array[]): ReadableStream<Uint8Array> {
    return new ReadableStream({
        start(controller) {
            for (const chunk of chunks) controller.enqueue(chunk);
            controller.close();
        },
    });
}

function okResponse(chunks: Uint8Array[]): Response {
    return new Response(streamOf(chunks), {status: 200, headers: {'Content-Type': 'text/event-stream'}});
}

const RESULT = {event: 'enricher_result', code: 'mockenrich', identifier_type: 'ISIN', identifier: 'IE00BK5BQT80', status: 'found', name: 'Vanguard FTSE All-World — Accumulating', page_url: null, identifiers: {}, conflicts: {}, error: null};
const DONE = {event: 'done', found_order: ['mockenrich'], default_order: ['mockenrich'], identifiers: {ISIN: 'IE00BK5BQT80'}};
const sse = (payload: object) => `data: ${JSON.stringify(payload)}\n\n`;

describe('the parser', () => {
    it('hands over an event split across two chunks only once it is whole', () => {
        const parser = createSseParser();
        const text = sse(RESULT);
        const cut = Math.floor(text.length / 2);
        expect(parser.push(encoder.encode(text.slice(0, cut)))).toEqual([]);
        expect(parser.push(encoder.encode(text.slice(cut)))).toEqual([RESULT]);
    });

    it('keeps a multi-byte character split across two chunks', () => {
        const parser = createSseParser();
        const bytes = encoder.encode(sse(RESULT));
        const dash = encoder.encode('—');
        const at = bytes.findIndex((_, index) => bytes[index] === dash[0] && bytes[index + 1] === dash[1]);
        expect(at).toBeGreaterThan(0);
        expect(parser.push(bytes.slice(0, at + 1))).toEqual([]);
        expect(parser.push(bytes.slice(at + 1))).toEqual([RESULT]);
    });

    it('hands over two events of one chunk as two, and skips a line that is not JSON', () => {
        const parser = createSseParser();
        expect(parser.push(encoder.encode(`${sse(RESULT)}data: not json\n\n${sse(DONE)}`))).toEqual([RESULT, DONE]);
    });
});

describe('the call', () => {
    const REQUEST = {asset_type: 'ETF', identifiers: {ISIN: 'IE00BK5BQT80'}, price_provider_code: null};

    it('posts the request with the session cookie, hands over every event and answers done', async () => {
        const fetchImpl = vi.fn().mockResolvedValue(okResponse([encoder.encode(sse(RESULT)), encoder.encode(sse(DONE))]));
        const seen: RecognizeEvent[] = [];
        const outcome = await recognizeEnrichers(REQUEST, {onEvent: (event) => seen.push(event), fetchImpl});
        expect(fetchImpl).toHaveBeenCalledOnce();
        const [path, init] = fetchImpl.mock.calls[0];
        expect(path).toBe(RECOGNIZE_PATH);
        expect(init.method).toBe('POST');
        expect(init.credentials).toBe('same-origin');
        expect(JSON.parse(init.body)).toEqual(REQUEST);
        expect(seen).toEqual([RESULT, DONE]);
        expect(outcome).toEqual({kind: 'done', done: DONE});
    });

    it('answers null for a stream that ends without done', async () => {
        const fetchImpl = vi.fn().mockResolvedValue(okResponse([encoder.encode(sse(RESULT))]));
        expect(await recognizeEnrichers(REQUEST, {onEvent: () => undefined, fetchImpl})).toEqual({kind: 'done', done: null});
    });

    it('answers a 429 as a refusal with its wait', async () => {
        const body = JSON.stringify({detail: {error_code: 'PROBE_RATE_LIMITED', retry_after: 12, message: 'Too many'}});
        const fetchImpl = vi.fn().mockResolvedValue(new Response(body, {status: 429, headers: {'Retry-After': '12'}}));
        expect(await recognizeEnrichers(REQUEST, {onEvent: () => undefined, fetchImpl})).toEqual({kind: 'refused', retryAfter: 12});
    });

    it('throws on another failure', async () => {
        const fetchImpl = vi.fn().mockResolvedValue(new Response('{}', {status: 500}));
        await expect(recognizeEnrichers(REQUEST, {onEvent: () => undefined, fetchImpl})).rejects.toThrow();
    });

    it('stops quietly when aborted', async () => {
        const controller = new AbortController();
        const fetchImpl = vi.fn().mockImplementation(() => {
            controller.abort();
            return Promise.reject(new DOMException('Aborted', 'AbortError'));
        });
        expect(await recognizeEnrichers(REQUEST, {onEvent: () => undefined, fetchImpl, signal: controller.signal})).toEqual({kind: 'aborted'});
    });
});
