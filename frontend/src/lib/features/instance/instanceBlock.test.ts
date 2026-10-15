// @vitest-environment jsdom
/**
 * instanceBlock — whether the hosting provider blocked this instance (workstream H, CP6, decision D4).
 *
 * The contract under test:
 *   - `isInstanceBlockedError(status, data)` is true only for status 423 with `data.detail.code === 'instance_blocked'`:
 *     another status, another code, a code outside `detail`, a `detail` that is not an object, or no body at all is
 *     not the block;
 *   - `instanceBlock.blocked` starts off, `markBlocked()` turns it on (twice is still on), `clear()` turns it off;
 *   - the getter is reactive: an effect reading it re-runs when the flag changes, as the `(app)` layout needs;
 *   - a change of account clears it (`registerClientSessionReset`): the first identity the session resolves changes
 *     nothing, the next different one clears the flag, and the same account again leaves it as it is.
 *
 * The flag is module-level `$state` and the reset is registered at import, so every test takes a freshly imported
 * graph (`vi.resetModules()` + `import()`): the store, the client session it registers with, and the rune helpers of
 * the same graph, so that an effect of the test tracks the store's own signal. jsdom, because effects run only there.
 */
import {describe, expect, it, vi} from 'vitest';

/** The store of a page load that has just begun, with the client session and the rune helpers of the same graph. */
async function freshPageLoad() {
    vi.resetModules();
    const store = await import('./instanceBlock.svelte');
    const session = await import('$lib/stores/app/clientSession');
    const runes = await import('$test/runes.svelte');
    const {flushSync} = await import('svelte');
    return {...store, ...session, ...runes, flushSync};
}

const BLOCKED_BODY = {detail: {code: 'instance_blocked', message: 'This instance is blocked by its hosting provider'}};

describe('isInstanceBlockedError — the refusal of a blocked instance', () => {
    it.each([
        ['423 with the code and the message', 423, BLOCKED_BODY],
        ['423 with the code alone', 423, {detail: {code: 'instance_blocked'}}],
    ])('is true for %s', async (_case, status, data) => {
        const {isInstanceBlockedError, INSTANCE_BLOCKED_STATUS, INSTANCE_BLOCKED_CODE} = await freshPageLoad();

        expect([INSTANCE_BLOCKED_STATUS, INSTANCE_BLOCKED_CODE]).toEqual([423, 'instance_blocked']);
        expect(isInstanceBlockedError(status, data)).toBe(true);
    });

    it.each([
        ['a 403 with the same body', 403, BLOCKED_BODY],
        ['a 401 with the same body', 401, BLOCKED_BODY],
        ['a 200 with the same body', 200, BLOCKED_BODY],
        ['no status', undefined, BLOCKED_BODY],
        ['423 with another code', 423, {detail: {code: 'locked'}}],
        ['423 with the code in another case', 423, {detail: {code: 'INSTANCE_BLOCKED'}}],
        ['423 with the code outside detail', 423, {code: 'instance_blocked'}],
        ['423 with a string detail', 423, {detail: 'instance_blocked'}],
        ['423 with a null detail', 423, {detail: null}],
        ['423 with an array detail', 423, {detail: [{code: 'instance_blocked'}]}],
        ['423 with an empty body', 423, {}],
        ['423 with a null body', 423, null],
        ['423 without a body', 423, undefined],
        ['423 with a text body', 423, 'instance_blocked'],
    ])('is false for %s', async (_case, status, data) => {
        const {isInstanceBlockedError} = await freshPageLoad();

        expect(isInstanceBlockedError(status, data)).toBe(false);
    });
});

describe('instanceBlock — the flag', () => {
    it('starts off, is turned on by markBlocked, stays on when marked again, and is turned off by clear', async () => {
        const {instanceBlock} = await freshPageLoad();

        expect(instanceBlock.blocked, 'a page load starts unblocked').toBe(false);
        instanceBlock.markBlocked();
        expect(instanceBlock.blocked).toBe(true);
        instanceBlock.markBlocked();
        expect(instanceBlock.blocked, 'a second refusal changes nothing').toBe(true);
        instanceBlock.clear();
        expect(instanceBlock.blocked).toBe(false);
    });

    it('is reactive: an effect reading it re-runs on each change', async () => {
        const {instanceBlock, recordReads, assertEffectsRun, flushSync} = await freshPageLoad();
        assertEffectsRun();
        const reads = recordReads(() => instanceBlock.blocked);

        instanceBlock.markBlocked();
        flushSync();
        instanceBlock.clear();
        flushSync();
        reads.stop();

        expect(reads.values, 'the layout re-renders on the first refusal, and again when it is cleared').toEqual([false, true, false]);
    });
});

describe('instanceBlock — a change of account clears it', () => {
    it('is cleared when the session moves to another account, and kept for the same one', async () => {
        const {instanceBlock, transitionClientSession} = await freshPageLoad();
        transitionClientSession(7);
        instanceBlock.markBlocked();

        expect(transitionClientSession(7), 'Barrier: the same account is no transition').toBe(false);
        expect(instanceBlock.blocked, 'the same account keeps the block').toBe(true);

        expect(transitionClientSession(8), 'Barrier: another account is a transition').toBe(true);
        expect(instanceBlock.blocked, 'another account starts unblocked: its first refusal will tell').toBe(false);
    });

    it('is cleared on sign-out too, the session moving to no account', async () => {
        const {instanceBlock, transitionClientSession} = await freshPageLoad();
        transitionClientSession('7');
        instanceBlock.markBlocked();

        expect(transitionClientSession(null)).toBe(true);
        expect(instanceBlock.blocked).toBe(false);
    });

    it('is not cleared by the first identity the session resolves, which is no change of account', async () => {
        const {instanceBlock, transitionClientSession} = await freshPageLoad();
        instanceBlock.markBlocked();

        expect(transitionClientSession(7), 'Barrier: the first identity is resolved').toBe(true);
        expect(instanceBlock.blocked, 'resolving the account that got the refusal must not lift the block').toBe(true);
    });
});
