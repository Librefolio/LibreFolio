// @vitest-environment jsdom
/**
 * profileAutoAsk (plan 68, E8b): the life of the automatic «Chiedi» in the asset window, as `enricherRecognition` is
 * the life of «Riconosci».
 *
 * Pinned:
 * - one question per (type, list): the same never twice, a new one drops the answer of the old, late ones too;
 * - the answer is handed over once, when it is the current question's;
 * - a 429 (the per-user limit) is a state with its wait, no retry; another failure a state too, never a throw;
 * - `cancel` (the asset created, the window closed) drops what is in flight.
 */
import {describe, expect, it, vi} from 'vitest';
import {createProfileAutoAsk} from './profileAutoAsk.svelte';
import type {AskAnswer} from './profileEditState';

const ANSWER: AskAnswer = {voices: {fund_provider: {value: 'Vanguard', source: 'justetf'}}, outcomes: [{code: 'justetf', status: 'ok'}]};
const REQUEST = {asset_type: 'ETF', enrichers: {justetf: {identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'}}};
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

function deferredAsk() {
    const calls: Array<{request: unknown; resolve: (answer: AskAnswer) => void; reject: (error: unknown) => void}> = [];
    const ask = vi.fn((request: unknown) => new Promise<AskAnswer>((resolve, reject) => calls.push({request, resolve, reject})));
    return {ask, calls};
}

describe('profileAutoAsk', () => {
    it('asks once per question and hands the answer over', async () => {
        const {ask, calls} = deferredAsk();
        const onanswer = vi.fn();
        const state = createProfileAutoAsk(ask, onanswer);
        expect(state.start(REQUEST)).toBe(true);
        expect(state.start({...REQUEST, enrichers: {...REQUEST.enrichers}})).toBe(false);
        expect(ask).toHaveBeenCalledOnce();
        expect(state.status).toBe('running');
        calls[0].resolve(ANSWER);
        await flush();
        expect(state.status).toBe('done');
        expect(onanswer).toHaveBeenCalledWith(ANSWER);
    });

    it('drops the answer of a question a new one replaced', async () => {
        const {ask, calls} = deferredAsk();
        const onanswer = vi.fn();
        const state = createProfileAutoAsk(ask, onanswer);
        state.start(REQUEST);
        state.start({...REQUEST, asset_type: 'FUND'});
        calls[0].resolve(ANSWER);
        await flush();
        expect(onanswer).not.toHaveBeenCalled();
        calls[1].resolve(ANSWER);
        await flush();
        expect(onanswer).toHaveBeenCalledOnce();
    });

    it('waits out a refusal for too many requests and asks again by itself (PROF, E8c)', async () => {
        vi.useFakeTimers();
        try {
            const {ask, calls} = deferredAsk();
            const onanswer = vi.fn();
            const state = createProfileAutoAsk(ask, onanswer);
            state.start(REQUEST);
            calls[0].reject({response: {status: 429, data: {detail: {error_code: 'PROBE_RATE_LIMITED', retry_after: 20}}}});
            await vi.advanceTimersByTimeAsync(19_000);
            expect(state.status).toBe('refused');
            expect(ask).toHaveBeenCalledOnce();
            await vi.advanceTimersByTimeAsync(1_000);
            expect(ask).toHaveBeenCalledTimes(2);
            expect(ask.mock.calls[1][0]).toEqual(REQUEST);
            calls[1].resolve(ANSWER);
            await vi.advanceTimersByTimeAsync(0);
            expect(state.status).toBe('done');
            expect(onanswer).toHaveBeenCalledWith(ANSWER);
        } finally {
            vi.useRealTimers();
        }
    });

    it('says a refusal for too many requests with its wait, and another failure, as states', async () => {
        const {ask, calls} = deferredAsk();
        const state = createProfileAutoAsk(ask, vi.fn());
        state.start(REQUEST);
        calls[0].reject({response: {status: 429, data: {detail: {error_code: 'PROBE_RATE_LIMITED', retry_after: 20}}}});
        await flush();
        expect(state.status).toBe('refused');
        expect(state.retryAfter).toBe(20);

        state.start({...REQUEST, asset_type: 'FUND'});
        calls[1].reject(new Error('network'));
        await flush();
        expect(state.status).toBe('error');
    });

    it('drops the answer in flight when cancelled, and asks again the same question after', async () => {
        const {ask, calls} = deferredAsk();
        const onanswer = vi.fn();
        const state = createProfileAutoAsk(ask, onanswer);
        state.start(REQUEST);
        state.cancel();
        calls[0].resolve(ANSWER);
        await flush();
        expect(onanswer).not.toHaveBeenCalled();
        expect(state.status).toBe('idle');
        expect(state.start(REQUEST)).toBe(true);
    });
});
