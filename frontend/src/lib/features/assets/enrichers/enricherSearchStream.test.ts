/**
 * enricherSearchStream (ENR-3): «Cerca online» as the backend streams it (`GET /assets/enrichers/search`, Server-Sent
 * Events: `enricher_results`, last `done`).
 *
 * Pinned:
 * - the address carries the text, each code repeated, and the asset's type (omitted when there is none);
 * - every event is handed over as it arrives, across chunks split in the middle of a line, and the call answers done;
 * - a 429 is a typed refusal with its wait, never a throw; another failure throws; an abort stops quietly.
 */
import {describe, expect, it, vi} from 'vitest';
import {SEARCH_PATH, searchEnrichersOnline, searchUrl, type EnricherSearchEvent} from './enricherSearchStream';

const encoder = new TextEncoder();

function streamOf(chunks: Uint8Array[]): ReadableStream<Uint8Array> {
    return new ReadableStream({
        start(controller) {
            for (const chunk of chunks) controller.enqueue(chunk);
            controller.close();
        },
    });
}

const okResponse = (chunks: Uint8Array[]) => new Response(streamOf(chunks), {status: 200, headers: {'Content-Type': 'text/event-stream'}});
const sse = (payload: object) => `data: ${JSON.stringify(payload)}\n\n`;

const RESULTS: EnricherSearchEvent = {
    event: 'enricher_results',
    code: 'mockenrich',
    status: 'ok',
    via: 'search',
    results: [{name: 'Vanguard FTSE All-World', binding: {identifier_type: 'TICKER', identifier: 'VWRA'}}],
    accepted_identifier_types: ['TICKER', 'ISIN'],
    retry_after: null,
    error_code: null,
} as EnricherSearchEvent;
const DONE: EnricherSearchEvent = {event: 'done', codes: ['mockenrich', 'esma']};
const REQUEST = {q: 'vanguard world', codes: ['mockenrich', 'esma'], assetType: 'ETF'};

describe('the address', () => {
    it('repeats each code and carries the text and the asset type', () => {
        const url = new URL(searchUrl(REQUEST), 'http://localhost');
        expect(url.pathname).toBe(SEARCH_PATH);
        expect(url.searchParams.get('q')).toBe('vanguard world');
        expect(url.searchParams.getAll('codes')).toEqual(['mockenrich', 'esma']);
        expect(url.searchParams.get('asset_type')).toBe('ETF');
    });

    it('leaves the asset type out when there is none', () => {
        expect(new URL(searchUrl({q: 'x&y=1', codes: ['a']}), 'http://localhost').searchParams.has('asset_type')).toBe(false);
        expect(new URL(searchUrl({q: 'x&y=1', codes: ['a']}), 'http://localhost').searchParams.get('q')).toBe('x&y=1');
    });
});

describe('the call', () => {
    it('gets the address with the session cookie, hands over each event as it arrives and answers done', async () => {
        const fetchImpl = vi.fn().mockResolvedValue(okResponse([encoder.encode(sse(RESULTS)), encoder.encode(sse(DONE))]));
        const seen: EnricherSearchEvent[] = [];
        const outcome = await searchEnrichersOnline(REQUEST, {onEvent: (event) => seen.push(event), fetchImpl});
        expect(fetchImpl).toHaveBeenCalledOnce();
        const [url, init] = fetchImpl.mock.calls[0];
        expect(url).toBe(searchUrl(REQUEST));
        expect(init.method).toBe('GET');
        expect(init.credentials).toBe('same-origin');
        expect(seen).toEqual([RESULTS, DONE]);
        expect(outcome).toEqual({kind: 'done'});
    });

    it('keeps an event split across chunks until it is whole', async () => {
        const text = sse(RESULTS);
        const cut = Math.floor(text.length / 2);
        const seen: EnricherSearchEvent[] = [];
        const fetchImpl = vi.fn().mockResolvedValue(okResponse([encoder.encode(text.slice(0, cut)), encoder.encode(text.slice(cut) + sse(DONE))]));
        await searchEnrichersOnline(REQUEST, {onEvent: (event) => seen.push(event), fetchImpl});
        expect(seen).toEqual([RESULTS, DONE]);
    });

    it('answers a 429 as a refusal with its wait', async () => {
        const body = JSON.stringify({detail: {error_code: 'PROBE_RATE_LIMITED', retry_after: 7, message: 'Too many'}});
        const fetchImpl = vi.fn().mockResolvedValue(new Response(body, {status: 429, headers: {'Retry-After': '7'}}));
        expect(await searchEnrichersOnline(REQUEST, {onEvent: () => undefined, fetchImpl})).toEqual({kind: 'refused', retryAfter: 7});
    });

    it('throws on another failure', async () => {
        const fetchImpl = vi.fn().mockResolvedValue(new Response('{}', {status: 500}));
        await expect(searchEnrichersOnline(REQUEST, {onEvent: () => undefined, fetchImpl})).rejects.toThrow();
    });

    it('stops quietly when aborted', async () => {
        const controller = new AbortController();
        const fetchImpl = vi.fn().mockImplementation(() => {
            controller.abort();
            return Promise.reject(new DOMException('Aborted', 'AbortError'));
        });
        expect(await searchEnrichersOnline(REQUEST, {onEvent: () => undefined, fetchImpl, signal: controller.signal})).toEqual({kind: 'aborted'});
    });
});
