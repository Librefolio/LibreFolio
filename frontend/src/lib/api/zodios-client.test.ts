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
 * `$app/environment` reports `browser: false`, so the 401 branch stays inert (it would navigate to the login) — but in
 * the describe of the 401, which turns it on. `instanceBlock` is the real store, imported statically so that it is
 * the very module the interceptor marks.
 *
 * Accounts lot A7b (decided by the coordinator, 2026-10-16 21:10; closes A-13): a 401 sends the browser to the login,
 * carrying the page to come back to (`goto(loginUrl(pathname + search))`), except where the login is already there
 * (`/`) and — new — on the anonymous pages of a link, whose `window.location.pathname` is exactly `/setup`, `/invite`,
 * `/reset-password` or `/verify-email`, with or without a trailing slash. There nobody is signed in, the 401 is the
 * blocked instance refusing an anonymous caller (`backend/app/api/v1/instance_block.py`), and the page explains it;
 * the login would lose the token of the link. A path that only begins like one of them (`/setup-something`,
 * `/invites`, `/setup/extra`) still goes to the login. The 423 handling is unchanged, on those pages too. The red
 * cases are the link pages; the rest of that describe guards today's behaviour. For it `browser` is switched on: the
 * module mock is a proxy over `mocks.environment` itself, read at every access (as in `FilePreviewModal.test.ts`), and
 * the address is jsdom's own, set with `history.replaceState` and put back to `/` after each test. With `browser` on
 * the request interceptor reads `localStorage`, which jsdom under this Node build does not provide: that describe
 * installs an in-memory one of its own for each case and puts the previous descriptors back after it.
 *
 * Lot H-62 (the «awaiting restore» mode): while the hosting panel restores the instance on an empty volume, every route
 * but `GET /system/instance` answers `423 {"detail": {"code": "instance_awaiting_restore"}}`. On such an answer the
 * interceptor forces `instanceConfig.load({force: true})`, so that the root layout's `AwaitingRestoreGate` reads the
 * new `mode` even when the configuration was read before the mode began; the error still reaches the caller unchanged,
 * and the instance block stays off. A 423 `instance_blocked`, a 423 with another code, a 403 with the same body and a
 * success force nothing. `instanceConfig.svelte` is a mock whose `load` is the spy. The client must not import that
 * rune module statically (`apiClientRuneFree.gate.test.ts`), so the call is expected to go through a dynamic `import()`
 * and to land a few microtasks after the refusal: the positive case polls for it (`expect.poll`, a deadline, no
 * sleep); a negative case sends a positive request after its own, then drains the lazy import queue (its own
 * `import()` of the same module, which settles after the ones the interceptor started before it) and polls until the
 * positive call landed: by then a call of the negative request, started first, would have landed too. Red until H-62:
 * nothing calls `load`.
 *
 * Lot B-33, the start's part (an unreadable restore state serves no data): while the state of a restore cannot be read
 * every route but a few answers `423 {"detail": {"code": "instance_restore_interrupted"}}` to anyone. On such an answer
 * the interceptor forces `instanceConfig.load({force: true})` exactly as for `instance_awaiting_restore` (the helper
 * `isInstanceRestoreInterruptedError` of `instanceBlockState.ts`, its own spec `instanceBlockState.test.ts`), so the
 * root gate reads `restore_interrupted`; the error still reaches the caller unchanged, the block stays off, nothing
 * navigates. A 423 `instance_blocked`, a 423 with another code, a 403 with the same body and a success force nothing.
 * Same method as the H-62 describe. Red until B-33: nothing calls `load` on that code (the negative cases too, through
 * their positive control).
 */
import {AxiosError, type AxiosAdapter, type AxiosResponse} from 'axios';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const mocks = vi.hoisted(() => ({
    goto: vi.fn().mockName('goto'),
    notifyPortfolioMutation: vi.fn().mockName('notifyPortfolioMutation'),
    loadInstanceConfig: vi.fn(() => Promise.resolve()).mockName('instanceConfig.load'),
    /** What `$app/environment` exports: `browser` is off but in the describe of the 401. */
    environment: {browser: false, dev: true, building: false, version: 'test'},
}));

vi.mock('$app/environment', () => mocks.environment);
vi.mock('$app/navigation', () => ({goto: mocks.goto}));
vi.mock('$lib/debug', () => ({debug: {log: vi.fn(), warn: vi.fn(), error: vi.fn(), info: vi.fn()}, isDebugEnabled: () => false}));
vi.mock('$lib/stores/portfolio/portfolioMutation', () => ({notifyPortfolioMutation: mocks.notifyPortfolioMutation}));
// The client stub takes plugins: the module installs its 'zod-validation' plugin with `use` when it loads (H-60).
vi.mock('./generated', () => ({createApiClient: vi.fn(() => ({use: vi.fn()}))}));
// H-62: the configuration the root gate reads; the interceptor forces a reload of it on a 423 instance_awaiting_restore.
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({instanceConfig: {load: mocks.loadInstanceConfig}}));

import {axiosInstance} from './zodios-client';
import {instanceBlock} from '$lib/features/instance/instanceBlock.svelte';
import {loginUrl} from '$lib/utils/internalPath';

const BLOCKED_BODY = {detail: {code: 'instance_blocked', message: 'This instance is blocked by its hosting provider'}};
const AWAITING_RESTORE_BODY = {detail: {code: 'instance_awaiting_restore', message: 'This instance is waiting for a restore'}};
const RESTORE_INTERRUPTED_BODY = {detail: {code: 'instance_restore_interrupted', message: 'The state of the restore cannot be read'}};

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
    mocks.loadInstanceConfig.mockClear();
    mocks.environment.browser = false;
});

afterEach(() => {
    mocks.environment.browser = false;
    window.history.replaceState(null, '', '/');
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

describe('zodios-client — a 423 instance_awaiting_restore reloads the instance config (H-62)', () => {
    /** The lazy import queue drained: an `import()` of the module the interceptor loads lazily, then its continuations. */
    async function drainLazyImports(): Promise<void> {
        await import('$lib/features/instance/instanceConfig.svelte');
        await Promise.resolve();
        await Promise.resolve();
    }

    it('forces instanceConfig.load({force: true}), and the caller still receives the refusal', async () => {
        const error = await requestAnswered(423, AWAITING_RESTORE_BODY);

        expect(error, 'the refusal must reach the caller').toBeInstanceOf(AxiosError);
        expect([error?.response?.status, error?.response?.data]).toEqual([423, AWAITING_RESTORE_BODY]);
        await expect.poll(() => mocks.loadInstanceConfig.mock.calls.length, {timeout: 2_000}).toBeGreaterThanOrEqual(1);
        expect(mocks.loadInstanceConfig).toHaveBeenCalledWith(expect.objectContaining({force: true}));
        expect(instanceBlock.blocked, 'awaiting a restore is not a block').toBe(false);
        expect(mocks.goto, 'a 423 never navigates').not.toHaveBeenCalled();
    });

    it.each([
        ['a 423 instance_blocked', 423, BLOCKED_BODY],
        ['a 423 with another code', 423, {detail: {code: 'locked'}}],
        ['a 423 without a body', 423, undefined],
        ['a 403 with the same body', 403, AWAITING_RESTORE_BODY],
        ['a success', 200, {status: 'ok'}],
    ])('forces nothing on %s', async (_case, status, data) => {
        const error = await requestAnswered(status, data);
        expect(error?.response?.status ?? 200, 'Barrier: the request was answered with the status of the case').toBe(status);

        // Positive control after it: once its forced load landed, one from the case's request would have landed too.
        await requestAnswered(423, AWAITING_RESTORE_BODY);
        await drainLazyImports();
        await expect.poll(() => mocks.loadInstanceConfig.mock.calls.length, {timeout: 2_000}).toBeGreaterThanOrEqual(1);
        await drainLazyImports();

        expect(mocks.loadInstanceConfig, `${status} is not the refusal of an instance awaiting a restore: only the control forced a load`).toHaveBeenCalledTimes(1);
    });
});

describe('zodios-client — a 423 instance_restore_interrupted reloads the instance config (B-33)', () => {
    /** The lazy import queue drained: an `import()` of the module the interceptor loads lazily, then its continuations. */
    async function drainLazyImports(): Promise<void> {
        await import('$lib/features/instance/instanceConfig.svelte');
        await Promise.resolve();
        await Promise.resolve();
    }

    it('forces instanceConfig.load({force: true}), and the caller still receives the refusal', async () => {
        const error = await requestAnswered(423, RESTORE_INTERRUPTED_BODY);

        expect(error, 'the refusal must reach the caller').toBeInstanceOf(AxiosError);
        expect([error?.response?.status, error?.response?.data]).toEqual([423, RESTORE_INTERRUPTED_BODY]);
        await expect.poll(() => mocks.loadInstanceConfig.mock.calls.length, {timeout: 2_000}).toBeGreaterThanOrEqual(1);
        expect(mocks.loadInstanceConfig).toHaveBeenCalledWith(expect.objectContaining({force: true}));
        expect(instanceBlock.blocked, 'an interrupted restore is not a block').toBe(false);
        expect(mocks.goto, 'a 423 never navigates').not.toHaveBeenCalled();
    });

    it.each([
        ['a 423 instance_blocked', 423, BLOCKED_BODY],
        ['a 423 with another code', 423, {detail: {code: 'locked'}}],
        ['a 423 without a body', 423, undefined],
        ['a 403 with the same body', 403, RESTORE_INTERRUPTED_BODY],
        ['a success', 200, {status: 'ok'}],
    ])('forces nothing on %s', async (_case, status, data) => {
        const error = await requestAnswered(status, data);
        expect(error?.response?.status ?? 200, 'Barrier: the request was answered with the status of the case').toBe(status);

        // Positive control after it: once its forced load landed, one from the case's request would have landed too.
        await requestAnswered(423, RESTORE_INTERRUPTED_BODY);
        await drainLazyImports();
        await expect.poll(() => mocks.loadInstanceConfig.mock.calls.length, {timeout: 2_000}).toBeGreaterThanOrEqual(1);
        await drainLazyImports();

        expect(mocks.loadInstanceConfig, `${status} is not the refusal of an interrupted restore: only the control forced a load`).toHaveBeenCalledTimes(1);
    });
});

describe('zodios-client — a 401 goes to the login, but not from the anonymous page of a link (A7b, A-13)', () => {
    /** The anonymous pages of a link, as `window.location.pathname` reads them: exactly these, or these and a slash. */
    const LINK_PAGES = ['/setup', '/invite', '/reset-password', '/verify-email'];
    const LINK_PAGES_BOTH_WAYS = [...LINK_PAGES, ...LINK_PAGES.map((path) => `${path}/`)];
    /** The 401 a blocked instance gives an anonymous caller: `get_current_user`'s. */
    const NOT_AUTHENTICATED = {detail: 'Not authenticated'};

    /** Puts `path` in jsdom's address bar. */
    function openAt(path: string): void {
        window.history.replaceState(null, '', path);
    }

    /**
     * A local storage this describe owns, the in-memory stand-in of `AboutTab.test.ts`. With `browser` on, the REQUEST
     * interceptor reads the language from `localStorage` (`getCurrentLanguage`) before the transport is reached, and
     * jsdom under this Node build exposes no usable one (Node: «localStorage is not available because
     * --localstorage-file was not provided»): the TypeError rejected every request before the adapter answered, so no
     * case reached the 401 branch and every Barrier failed on an `error.response` that was never there. An assumption
     * of the test about its environment, not a product defect. Installed on `globalThis` and `window` for each case;
     * the descriptors found there are put back after it, so the other describes and files keep the environment they had.
     */
    const stored = new Map<string, string>();
    const localStorageStub = {
        getItem: (key: string) => stored.get(key) ?? null,
        setItem: (key: string, value: string) => void stored.set(key, String(value)),
        removeItem: (key: string) => void stored.delete(key),
        clear: () => stored.clear(),
        key: (index: number) => [...stored.keys()][index] ?? null,
        get length() {
            return stored.size;
        },
    };
    /** What `localStorage` was on each target before the stand-in: its own descriptor, `undefined` where it had none. */
    let storageBefore: Array<{target: object; descriptor: PropertyDescriptor | undefined}> = [];

    beforeEach(() => {
        // In the browser: the branch of the 401 is live, and the request interceptor reads the language from storage.
        mocks.environment.browser = true;
        stored.clear();
        // Every descriptor is read before any is replaced: in this environment `window` may be `globalThis` itself.
        storageBefore = [globalThis, window].map((target) => ({target, descriptor: Object.getOwnPropertyDescriptor(target, 'localStorage')}));
        for (const {target} of storageBefore) Object.defineProperty(target, 'localStorage', {value: localStorageStub, configurable: true, writable: true});
        // The bare identifier, as the interceptor reads it.
        expect(typeof localStorage?.getItem, 'premise: the browser has a localStorage the test owns').toBe('function');
    });

    afterEach(() => {
        // Put back what was there, the last replaced first; a property that was not there goes again.
        for (const {target, descriptor} of storageBefore.reverse()) {
            if (descriptor) Object.defineProperty(target, 'localStorage', descriptor);
            else Reflect.deleteProperty(target, 'localStorage');
        }
        storageBefore = [];
    });

    // red until A7b
    it.each(LINK_PAGES_BOTH_WAYS)('stays on %s: no login, and the page receives the 401 to explain it', async (path) => {
        openAt(path);
        expect(window.location.pathname, 'premise: the address is the page of the case').toBe(path);

        const error = await requestAnswered(401, NOT_AUTHENTICATED);

        expect([error?.response?.status, error?.response?.data], 'Barrier: the 401 went through the interceptor and reached the caller unchanged').toEqual([401, NOT_AUTHENTICATED]);
        expect(mocks.goto, `a 401 on ${path} goes nowhere: the login would lose the link`).not.toHaveBeenCalled();
    });

    // red until A7b
    it('decides on the path alone: a query on the page of a link changes nothing', async () => {
        openAt('/setup?lang=it');

        const error = await requestAnswered(401, NOT_AUTHENTICATED);

        expect(error?.response?.status, 'Barrier: the 401 reached the caller').toBe(401);
        expect(mocks.goto).not.toHaveBeenCalled();
    });

    // guard — and the positive control of the reds above: were `browser` not live in the interceptor, no path would
    // navigate, these would turn red, and the link pages' «no goto» would be passing vacuously.
    it.each(['/dashboard', '/settings', '/settings?tab=users', '/setup-something', '/invites', '/setup/extra'])('still sends %s to the login, carrying the page to come back to', async (path) => {
        openAt(path);

        const error = await requestAnswered(401, NOT_AUTHENTICATED);

        expect(error?.response?.status, 'Barrier: the 401 reached the caller').toBe(401);
        expect(mocks.goto, 'one navigation').toHaveBeenCalledTimes(1);
        expect(mocks.goto, 'to the login, as today').toHaveBeenCalledWith(loginUrl(path));
    });

    // guard
    it('sends nothing from /: the login is already there, and a failed sign-in answers 401 too', async () => {
        openAt('/');

        const error = await requestAnswered(401, {detail: 'Invalid credentials'});

        expect(error?.response?.status, 'Barrier: the 401 reached the caller').toBe(401);
        expect(mocks.goto).not.toHaveBeenCalled();
    });

    // guard
    it.each(LINK_PAGES_BOTH_WAYS)('still turns the block on for a 423 instance_blocked on %s, and goes nowhere', async (path) => {
        openAt(path);

        const error = await requestAnswered(423, BLOCKED_BODY);

        expect([error?.response?.status, error?.response?.data], 'the refusal reaches the caller').toEqual([423, BLOCKED_BODY]);
        expect(instanceBlock.blocked, 'the 423 handling does not depend on the page').toBe(true);
        expect(mocks.goto, 'a 423 never navigated, and does not start to').not.toHaveBeenCalled();
    });
});
