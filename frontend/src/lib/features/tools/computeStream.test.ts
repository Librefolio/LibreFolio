/**
 * The line reader of the Tool streaming route (lot V1 of project 67): `POST /api/v1/tools/compute/stream` answers one
 * JSON object per line, progress lines first and the result line last. These cases drive the reader with a fake
 * `fetch` whose body arrives in awkward chunks; the progress codec is the generated one (`./dev.py api sync`).
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

const {observeFetchAnswer} = vi.hoisted(() => ({observeFetchAnswer: vi.fn((_url: string, _answer: unknown) => null as unknown)}));

vi.mock('$lib/api', () => ({
    apiRequestHeaders: () => ({'Accept-Language': 'it'}),
    observeFetchAnswer,
}));

import {ToolClientError} from './contracts';
import {TOOL_COMPUTE_STREAM_PATH, postComputeStream, readStreamLines, type ToolProgress} from './computeStream';

const encoder = new TextEncoder();

function progress(phase: string, step: number | null = null, total: number | null = null): Record<string, unknown> {
    return {kind: 'progress', correlation_id: 'corr', phase, step, total, elapsed_ms: 3};
}

const RESULT = {kind: 'result', response: {request_id: 'r', results: []}};

function body(chunks: (string | Uint8Array)[]): ReadableStream<Uint8Array> {
    return new ReadableStream({
        start(controller) {
            for (const chunk of chunks) controller.enqueue(typeof chunk === 'string' ? encoder.encode(chunk) : chunk);
            controller.close();
        },
    });
}

function answer(stream: ReadableStream<Uint8Array>, status = 200): Response {
    return new Response(stream, {status, headers: {'Content-Type': 'application/x-ndjson'}});
}

async function lines(chunks: (string | Uint8Array)[]): Promise<string[]> {
    const out: string[] = [];
    for await (const line of readStreamLines(body(chunks))) out.push(line);
    return out;
}

function run(fetchImpl: typeof fetch, options: {signal?: AbortSignal; timeoutMs?: number} = {}): {events: ToolProgress[]; done: Promise<unknown>} {
    vi.stubGlobal('fetch', fetchImpl);
    const events: ToolProgress[] = [];
    const done = postComputeStream('{"request_id":"r"}', {signal: options.signal ?? new AbortController().signal, timeoutMs: options.timeoutMs ?? 5_000, onProgress: (event) => events.push(event)});
    return {events, done};
}

afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
    observeFetchAnswer.mockClear();
});

describe('readStreamLines', () => {
    it('joins a line split across chunks', async () => {
        expect(await lines(['{"a":', '1}\n{"b"', ':2}\n'])).toEqual(['{"a":1}', '{"b":2}']);
    });

    it('decodes a multi-byte character split across chunks once it is whole', async () => {
        const bytes = encoder.encode('{"t":"€π"}\n');
        expect(await lines([bytes.slice(0, 7), bytes.slice(7, 9), bytes.slice(9)])).toEqual(['{"t":"€π"}']);
    });

    it('keeps a last line without a newline, and everything sent in one chunk', async () => {
        expect(await lines(['{"a":1}\n{"b":2}'])).toEqual(['{"a":1}', '{"b":2}']);
    });

    it('skips empty lines', async () => {
        expect(await lines(['\n{"a":1}\n\n', '\n'])).toEqual(['{"a":1}']);
    });
});

describe('postComputeStream', () => {
    it('hands every progress line over, then returns the response of the result line', async () => {
        const fetchMock = vi.fn(async () => answer(body([`${JSON.stringify(progress('validate'))}\n`, `${JSON.stringify(progress('search', 1, 2))}\n${JSON.stringify(RESULT)}\n`])));
        const {events, done} = run(fetchMock as unknown as typeof fetch);

        expect(await done).toEqual(RESULT.response);
        expect(events.map((event) => [event.phase, event.step, event.total])).toEqual([
            ['validate', null, null],
            ['search', 1, 2],
        ]);
        const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
        expect(url).toBe(TOOL_COMPUTE_STREAM_PATH);
        expect(init.method).toBe('POST');
        expect(init.body).toBe('{"request_id":"r"}');
        expect(init.credentials).toBe('same-origin');
        expect(init.headers).toMatchObject({'Content-Type': 'application/json', Accept: 'application/x-ndjson', 'Accept-Language': 'it'});
        expect(observeFetchAnswer).toHaveBeenCalledWith(TOOL_COMPUTE_STREAM_PATH, expect.objectContaining({status: 200}));
    });

    it('ignores a line of an unknown kind and a malformed progress line', async () => {
        const {events, done} = run((async () => answer(body([`{"kind":"later"}\n{"kind":"progress","phase":7}\n${JSON.stringify(RESULT)}\n`]))) as unknown as typeof fetch);
        expect(await done).toEqual(RESULT.response);
        expect(events).toEqual([]);
    });

    it('a stream that ends without its result line is a broken answer', async () => {
        const {done} = run((async () => answer(body([`${JSON.stringify(progress('validate'))}\n`]))) as unknown as typeof fetch);
        await expect(done).rejects.toMatchObject({kind: 'protocol', code: 'invalid_response'});
    });

    it('a line that is not JSON is a broken answer', async () => {
        const {done} = run((async () => answer(body(['not json\n']))) as unknown as typeof fetch);
        await expect(done).rejects.toMatchObject({kind: 'protocol', code: 'invalid_response'});
    });

    it('an HTTP refusal goes through the API error handling and comes back as its error', async () => {
        const refusal = new Error('handled');
        observeFetchAnswer.mockImplementationOnce(() => refusal);
        const {done} = run((async () => new Response(JSON.stringify({detail: {code: 'queue_full', retryable: true}}), {status: 429, headers: {'Content-Type': 'application/json'}})) as unknown as typeof fetch);
        await expect(done).rejects.toBe(refusal);
        expect(observeFetchAnswer).toHaveBeenCalledWith(TOOL_COMPUTE_STREAM_PATH, expect.objectContaining({status: 429, data: {detail: {code: 'queue_full', retryable: true}}}));
    });

    it('a call nothing answers is a network failure, reported like an Axios one', async () => {
        const {done} = run((async () => {
            throw new TypeError('Failed to fetch');
        }) as unknown as typeof fetch);
        await expect(done).rejects.toMatchObject({kind: 'network', code: 'network_failed'});
        expect(observeFetchAnswer).toHaveBeenCalledWith(TOOL_COMPUTE_STREAM_PATH, null);
    });

    it('the client timeout ends the wait as a timeout, not as a stop', async () => {
        vi.useFakeTimers();
        const fetchMock = vi.fn(
            (_url: string, init: RequestInit) =>
                new Promise<Response>((_resolve, reject) => {
                    init.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
                }),
        );
        const {done} = run(fetchMock as unknown as typeof fetch, {timeoutMs: 1_000});
        const outcome = expect(done).rejects.toMatchObject({kind: 'timeout', code: 'transport_timeout'});
        await vi.advanceTimersByTimeAsync(1_000);
        await outcome;
    });

    it('a stop while reading cancels the stream and is a stop', async () => {
        const stop = new AbortController();
        let cancelled = false;
        const stream = new ReadableStream<Uint8Array>({
            start(controller) {
                controller.enqueue(encoder.encode(`${JSON.stringify(progress('validate'))}\n`));
            },
            cancel() {
                cancelled = true;
            },
        });
        const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
            init.signal?.addEventListener('abort', () => undefined);
            return answer(stream);
        });
        vi.stubGlobal('fetch', fetchMock);
        const done = postComputeStream('{}', {signal: stop.signal, timeoutMs: 5_000, onProgress: () => stop.abort()});
        await expect(done).rejects.toBeInstanceOf(ToolClientError);
        await expect(done).rejects.toMatchObject({kind: 'aborted', code: 'waiting_stopped'});
        expect(cancelled).toBe(true);
    });
});
