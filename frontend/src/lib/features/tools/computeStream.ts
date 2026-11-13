/**
 * The Tool streaming route, read line by line (lot V1 of project 67, decisioni-REB §10.2).
 *
 * `POST /api/v1/tools/compute/stream` takes the request of `POST /api/v1/tools/compute` and answers one JSON object per
 * line: `{kind: "progress", …}` while the calculation runs, then `{kind: "result", response}`, where `response` is the
 * answer `/compute` gives. Axios cannot hand over a body while it arrives, so this one route is read with `fetch` and its
 * `ReadableStream`; failures go through the same API handling as an Axios call (`observeFetchAnswer`). If a proxy holds
 * the answer back, every line arrives at the end: the result is the same, only the progress comes late.
 */
import type {z} from 'zod';
import {apiRequestHeaders, observeFetchAnswer} from '$lib/api';
import {toolTransportSchemas} from '$lib/api/generated-tools';
import {ToolClientError} from './contracts';

export const TOOL_COMPUTE_STREAM_PATH = '/api/v1/tools/compute/stream';

/** One progress message: the phase a calculation is in, and «n of m» inside it. Never a datum of the scenario. */
export type ToolProgress = z.output<typeof toolTransportSchemas.computeProgress>;

export interface ComputeStreamOptions {
    /** Stop: the request and the reading are cancelled, and the server cancels the calculation. */
    signal: AbortSignal;
    /** The descriptor's client timeout, as for `/compute`: past it the wait ends as a timeout. */
    timeoutMs: number;
    onProgress: (event: ToolProgress) => void;
}

/** The lines of a byte stream, decoded as UTF-8 across chunk boundaries; empty lines are skipped. */
export async function* readStreamLines(body: ReadableStream<Uint8Array>): AsyncGenerator<string> {
    const reader = body.getReader();
    const decoder = new TextDecoder('utf-8', {fatal: true});
    let buffer = '';
    let finished = false;
    try {
        for (;;) {
            const {done, value} = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, {stream: true});
            let end = buffer.indexOf('\n');
            while (end >= 0) {
                const line = buffer.slice(0, end);
                buffer = buffer.slice(end + 1);
                if (line.trim()) yield line;
                end = buffer.indexOf('\n');
            }
        }
        buffer += decoder.decode();
        finished = true;
        if (buffer.trim()) yield buffer;
    } finally {
        // An early exit (the result read, a stop, a broken line) cancels the rest of the body.
        if (!finished) void reader.cancel().catch(() => undefined);
        reader.releaseLock();
    }
}

function parseLine(line: string): unknown {
    try {
        return JSON.parse(line);
    } catch {
        throw new ToolClientError('protocol', 'invalid_response');
    }
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

async function readRefusal(response: Response): Promise<unknown> {
    try {
        return await response.json();
    } catch {
        return undefined;
    }
}

/**
 * POST `body` (the exact JSON text `/compute` would carry) to the streaming route; every valid progress line goes to
 * `onProgress`, and the `response` of the result line comes back unvalidated, as Axios hands back `/compute`'s body.
 * A line that is not JSON, or a stream that ends without its result line, is a broken answer.
 */
export async function postComputeStream(body: string, {signal, timeoutMs, onProgress}: ComputeStreamOptions): Promise<unknown> {
    if (signal.aborted) throw new ToolClientError('aborted', 'waiting_stopped');
    const controller = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => {
        timedOut = true;
        controller.abort();
    }, timeoutMs);
    const stop = () => controller.abort();
    signal.addEventListener('abort', stop, {once: true});
    const ended = (): ToolClientError | null => {
        if (timedOut) return new ToolClientError('timeout', 'transport_timeout');
        if (signal.aborted) return new ToolClientError('aborted', 'waiting_stopped');
        return null;
    };
    try {
        let response: Response;
        try {
            response = await fetch(TOOL_COMPUTE_STREAM_PATH, {
                method: 'POST',
                body,
                credentials: 'same-origin',
                headers: {...apiRequestHeaders(), 'Content-Type': 'application/json', Accept: 'application/x-ndjson'},
                signal: controller.signal,
            });
        } catch (error) {
            const stopped = ended();
            if (stopped) throw stopped;
            observeFetchAnswer(TOOL_COMPUTE_STREAM_PATH, null);
            throw error instanceof ToolClientError ? error : new ToolClientError('network', 'network_failed');
        }
        if (!response.ok) {
            const refusal = observeFetchAnswer(TOOL_COMPUTE_STREAM_PATH, {status: response.status, headers: response.headers, data: await readRefusal(response)});
            throw refusal ?? new ToolClientError('http', 'request_rejected', {httpStatus: response.status});
        }
        observeFetchAnswer(TOOL_COMPUTE_STREAM_PATH, {status: response.status, headers: response.headers});
        if (!response.body) throw new ToolClientError('protocol', 'invalid_response');
        try {
            for await (const line of readStreamLines(response.body)) {
                const value = parseLine(line);
                if (!isRecord(value)) throw new ToolClientError('protocol', 'invalid_response');
                if (value.kind === 'result') return value.response;
                if (value.kind !== 'progress') continue; // a kind this client does not know yet
                const parsed = toolTransportSchemas.computeProgress.safeParse(value);
                if (!parsed.success) continue; // a progress line is never worth failing the calculation
                try {
                    onProgress(parsed.data);
                } catch {
                    // A listener's failure never ends the wait for the result.
                }
                const stopped = ended();
                if (stopped) throw stopped;
            }
        } catch (error) {
            throw ended() ?? (error instanceof ToolClientError ? error : new ToolClientError('protocol', 'invalid_response'));
        }
        throw ended() ?? new ToolClientError('protocol', 'invalid_response');
    } finally {
        clearTimeout(timer);
        signal.removeEventListener('abort', stop);
    }
}
