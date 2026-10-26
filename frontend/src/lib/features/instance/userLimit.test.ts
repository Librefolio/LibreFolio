// @vitest-environment jsdom
/**
 * userLimit — whether the instance is over its plan of users (workstream A, lot A5-7).
 *
 * While the active accounts outnumber `LIBREFOLIO_MAX_USERS` the backend answers a signed-in user `423` with
 * `detail.code` `user_limit_exceeded` (`backend/app/api/v1/user_limit.py`); the API client's interceptor marks it, and the
 * `(app)` layout shows the page instead of the app: the choice for an administrator, the wait for anyone else. Same shape as
 * `instanceBlock` (the plain state in `userLimitState.ts`, its reactive face in `userLimit.svelte.ts`).
 *
 * The contract under test:
 *   - `isUserLimitError(status, data)` is true only for status 423 with `data.detail.code === 'user_limit_exceeded'`:
 *     another status, the block's or the restore's code, a code outside `detail`, a `detail` that is not an object, or no
 *     body at all is not that refusal;
 *   - `userLimit.exceeded` starts off, `markExceeded()` turns it on (twice is still on), `clear()` turns it off;
 *   - the getter is reactive: an effect reading it re-runs on each change;
 *   - a change of account clears it; the first identity the session resolves does not.
 *
 * A freshly imported module graph per test (`vi.resetModules()`): the state registers its session reset at import.
 */
import {describe, expect, it, vi} from 'vitest';

async function freshPageLoad() {
    vi.resetModules();
    const store = await import('./userLimit.svelte');
    const session = await import('$lib/stores/app/clientSession');
    const runes = await import('$test/runes.svelte');
    const {flushSync} = await import('svelte');
    return {...store, ...session, ...runes, flushSync};
}

const BODY = {detail: {code: 'user_limit_exceeded', message: 'This instance has more active users than its plan holds'}};

describe('isUserLimitError — the refusal of an instance over its plan', () => {
    it.each([
        ['423 with the code and the message', 423, BODY],
        ['423 with the code alone', 423, {detail: {code: 'user_limit_exceeded'}}],
    ])('is true for %s', async (_case, status, data) => {
        const {isUserLimitError, USER_LIMIT_CODE} = await freshPageLoad();

        expect(USER_LIMIT_CODE).toBe('user_limit_exceeded');
        expect(isUserLimitError(status, data)).toBe(true);
    });

    it.each([
        ['a 403 with the same body', 403, BODY],
        ['a 401 with the same body', 401, BODY],
        ['no status', undefined, BODY],
        ['423 instance_blocked', 423, {detail: {code: 'instance_blocked'}}],
        ['423 instance_restore_interrupted', 423, {detail: {code: 'instance_restore_interrupted'}}],
        ['423 instance_awaiting_restore', 423, {detail: {code: 'instance_awaiting_restore'}}],
        ['423 with the code in another case', 423, {detail: {code: 'USER_LIMIT_EXCEEDED'}}],
        ['423 with the code outside detail', 423, {code: 'user_limit_exceeded'}],
        ['423 with a string detail', 423, {detail: 'user_limit_exceeded'}],
        ['423 with a null detail', 423, {detail: null}],
        ['423 with an array detail', 423, {detail: [{code: 'user_limit_exceeded'}]}],
        ['423 with a null body', 423, null],
        ['423 without a body', 423, undefined],
        ['423 with a text body', 423, 'user_limit_exceeded'],
    ])('is false for %s', async (_case, status, data) => {
        const {isUserLimitError} = await freshPageLoad();

        expect(isUserLimitError(status, data)).toBe(false);
    });

    it('is not the block, the awaiting mode or the interrupted restore, and they are not it', async () => {
        const {isUserLimitError} = await freshPageLoad();
        const {isInstanceBlockedError, isInstanceAwaitingRestoreError, isInstanceRestoreInterruptedError} = await import('./instanceBlockState');

        expect(isUserLimitError(423, BODY), 'Barrier: it is the refusal').toBe(true);
        expect([isInstanceBlockedError(423, BODY), isInstanceAwaitingRestoreError(423, BODY), isInstanceRestoreInterruptedError(423, BODY)]).toEqual([false, false, false]);
    });
});

describe('userLimit — the flag', () => {
    it('starts off, is turned on by markExceeded, stays on when marked again, and is turned off by clear', async () => {
        const {userLimit} = await freshPageLoad();

        expect(userLimit.exceeded, 'a page load starts under the limit').toBe(false);
        userLimit.markExceeded();
        expect(userLimit.exceeded).toBe(true);
        userLimit.markExceeded();
        expect(userLimit.exceeded, 'a second refusal changes nothing').toBe(true);
        userLimit.clear();
        expect(userLimit.exceeded).toBe(false);
    });

    it('is reactive: an effect reading it re-runs on each change', async () => {
        const {userLimit, recordReads, assertEffectsRun, flushSync} = await freshPageLoad();
        assertEffectsRun();
        const reads = recordReads(() => userLimit.exceeded);

        userLimit.markExceeded();
        flushSync();
        userLimit.clear();
        flushSync();
        reads.stop();

        expect(reads.values).toEqual([false, true, false]);
    });

    it('is on from the first read when it was marked before the reactive face was imported', async () => {
        vi.resetModules();
        const plain = await import('./userLimitState');
        plain.userLimitState.markExceeded();

        const {userLimit} = await import('./userLimit.svelte');

        expect(userLimit.exceeded).toBe(true);
    });
});

describe('userLimit — a change of account clears it', () => {
    it('is cleared when the session moves to another account, and kept for the same one', async () => {
        const {userLimit, transitionClientSession} = await freshPageLoad();
        transitionClientSession(7);
        userLimit.markExceeded();

        expect(transitionClientSession(7), 'Barrier: the same account is no transition').toBe(false);
        expect(userLimit.exceeded).toBe(true);

        expect(transitionClientSession(8), 'Barrier: another account is a transition').toBe(true);
        expect(userLimit.exceeded, 'another account starts under the limit: its first refusal will tell').toBe(false);
    });

    it('is not cleared by the first identity the session resolves', async () => {
        const {userLimit, transitionClientSession} = await freshPageLoad();
        userLimit.markExceeded();

        expect(transitionClientSession(7)).toBe(true);
        expect(userLimit.exceeded).toBe(true);
    });
});
