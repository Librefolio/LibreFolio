// @vitest-environment jsdom
/**
 * zodios-client — the response interceptor turns the instance block on (workstream H, CP6, decision D4).
 *
 * The contract under test: an API answer `423` with `detail.code === 'instance_blocked'` turns `instanceBlock.blocked`
 * on, and the error still reaches the caller unchanged; a 403, a 401, a 423 with another code and a success leave the
 * flag off. The `(app)` layout then shows the block page.
 *
 * The requests go through the real `axiosInstance` and its interceptors; only the transport is replaced, per request,
 * by an adapter that answers the status and body the test chose (as axios's own adapters do, a status outside 2xx is
 * a rejected `AxiosError` carrying the response). The generated client is a stub: building it is not the subject.
 * `$app/environment` reports `browser: false`, so the 401 branch stays inert (it would navigate to the login).
 * `instanceBlock` is the real store, imported statically so that it is the very module the interceptor marks.
 */
import {AxiosError, type AxiosAdapter, type AxiosResponse} from 'axios';
import {beforeEach, describe, expect, it, vi} from 'vitest';

const mocks = vi.hoisted(() => ({
    goto: vi.fn().mockName('goto'),
    notifyPortfolioMutation: vi.fn().mockName('notifyPortfolioMutation'),
}));

vi.mock('$app/environment', () => ({browser: false, dev: true, building: false, version: 'test'}));
vi.mock('$app/navigation', () => ({goto: mocks.goto}));
vi.mock('$lib/debug', () => ({debug: {log: vi.fn(), warn: vi.fn(), error: vi.fn(), info: vi.fn()}, isDebugEnabled: () => false}));
vi.mock('$lib/stores/portfolio/portfolioMutation', () => ({notifyPortfolioMutation: mocks.notifyPortfolioMutation}));
vi.mock('./generated', () => ({createApiClient: vi.fn(() => ({}))}));

import {axiosInstance} from './zodios-client';
import {instanceBlock} from '$lib/features/instance/instanceBlock.svelte';

const BLOCKED_BODY = {detail: {code: 'instance_blocked', message: 'This instance is blocked by its hosting provider'}};

/** A transport that answers `status` with `data`: resolved for 2xx, otherwise rejected with the response, as axios does. */
function answering(status: number, data: unknown): AxiosAdapter {
    return (config) => {
        const response = {data, status, statusText: String(status), headers: {}, config} as AxiosResponse;
        if (status >= 200 && status < 300) return Promise.resolve(response);
        return Promise.reject(new AxiosError(`Request failed with status code ${status}`, AxiosError.ERR_BAD_REQUEST, config, {}, response));
    };
}

/** GET through the real instance and its interceptors; the rejection the caller receives, or null on success. */
async function requestAnswered(status: number, data: unknown): Promise<AxiosError | null> {
    try {
        await axiosInstance.get('/probe', {adapter: answering(status, data)});
        return null;
    } catch (error) {
        return error as AxiosError;
    }
}

beforeEach(() => {
    instanceBlock.clear();
    mocks.goto.mockClear();
});

describe('zodios-client — a 423 instance_blocked turns the block on', () => {
    it('marks the instance blocked, and the caller still receives the refusal', async () => {
        const error = await requestAnswered(423, BLOCKED_BODY);

        expect(instanceBlock.blocked, 'the interceptor must turn the block on').toBe(true);
        expect(error, 'the refusal must reach the caller').toBeInstanceOf(AxiosError);
        expect([error?.response?.status, error?.response?.data]).toEqual([423, BLOCKED_BODY]);
    });

    it.each([
        ['a 403 with the same body', 403, BLOCKED_BODY],
        ['a 401', 401, {detail: 'Not authenticated'}],
        ['a 423 with another code', 423, {detail: {code: 'locked'}}],
        ['a 423 without a body', 423, undefined],
    ])('leaves the block off on %s, and the caller still receives the refusal', async (_case, status, data) => {
        const error = await requestAnswered(status, data);

        expect(error?.response?.status, 'Barrier: the request was refused with the status of the case').toBe(status);
        expect(instanceBlock.blocked, `${status} is not the refusal of a blocked instance`).toBe(false);
        expect(mocks.goto, 'the 401 branch is inert here: no navigation').not.toHaveBeenCalled();
    });

    it('leaves the block off on a success', async () => {
        const error = await requestAnswered(200, {status: 'ok'});

        expect(error).toBeNull();
        expect(mocks.notifyPortfolioMutation, 'Barrier: the success went through the response interceptor').toHaveBeenCalled();
        expect(instanceBlock.blocked).toBe(false);
    });
});
