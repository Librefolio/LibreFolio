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
 *
 * Workstream Z, Z-20 (N-Z20-2, H's option A): the state moves into the plain `instanceBlockState.ts` — no runes, so that
 * the API client, which marks it on a 423, loads without Svelte's compiler (the AI Export probe) — and this module stays
 * its reactive face for the `(app)` layout: a `$state` read from the plain state when the face is imported, kept in step
 * by a synchronous subscription, with `markBlocked`/`clear` the plain module's own. The cases of the last describe pin
 * what the layout relies on: a change made through the plain module shows in `instanceBlock.blocked` before anything is
 * awaited; a block marked before the face is imported is on from the face's first read (H's condition 2); one session
 * reset, registered by the plain module and by nothing else, clears both (H's condition 3). The plain module is loaded by
 * a computed specifier, so while it does not exist those cases fail with the contract in their message and the cases
 * above stay as they are. Red until `src/lib/features/instance/instanceBlockState.ts` exists.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

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

/** Z-20's plain state (`$lib/features/instance/instanceBlockState`), by a computed specifier: Vite does not resolve it when it transforms this file. */
const PLAIN_STATE_MODULE = './instanceBlockState';

/** The plain state as N-Z20-2 gives it: no runes, listeners called synchronously on every change. */
interface InstanceBlockState {
    readonly blocked: boolean;
    markBlocked(): void;
    clear(): void;
    subscribe(listener: () => void): () => void;
}

/** `instanceBlockState` from the module graph the case is in. */
async function importPlainState(): Promise<InstanceBlockState> {
    let module: Record<string, unknown>;
    try {
        module = (await import(/* @vite-ignore */ PLAIN_STATE_MODULE)) as Record<string, unknown>;
    } catch (error) {
        throw new Error(`src/lib/features/instance/instanceBlockState.ts does not exist yet: the block still lives in the module-level $state of instanceBlock.svelte.ts, which the API client imports and the AI Export probe cannot load without Svelte's compiler (${String(error)})`);
    }
    const state = module.instanceBlockState as Partial<InstanceBlockState> | undefined;
    for (const name of ['markBlocked', 'clear', 'subscribe'] as const) {
        expect(typeof state?.[name], `instanceBlockState.ts exports no instanceBlockState.${name}()`).toBe('function');
    }
    return state as InstanceBlockState;
}

describe('instanceBlock — the reactive face of the plain state (workstream Z, Z-20)', () => {
    const CLIENT_SESSION = '$lib/stores/app/clientSession';

    afterEach(() => {
        vi.doUnmock(CLIENT_SESSION);
        vi.resetModules();
    });

    it('instanceBlockState.markBlocked() and clear() turn instanceBlock.blocked on and off at once, nothing awaited between the call and the read', async () => {
        const {instanceBlock} = await freshPageLoad();
        const instanceBlockState = await importPlainState();
        expect(instanceBlock.blocked, 'premise: a page load starts unblocked').toBe(false);

        instanceBlockState.markBlocked();
        expect(instanceBlock.blocked, 'the API client marks the plain state on a 423: the face the (app) layout reads must be on in the same tick').toBe(true);
        instanceBlockState.clear();
        expect(instanceBlock.blocked, 'and off again the same way').toBe(false);
    });

    it('a block marked before the face is imported is on from the face’s first read (H’s condition 2)', async () => {
        vi.resetModules();
        const instanceBlockState = await importPlainState();
        instanceBlockState.markBlocked();

        const {instanceBlock} = await import('./instanceBlock.svelte');

        expect(instanceBlock.blocked, 'the face starts from the plain state as it is when the face is imported: a 423 that came before the layout loaded is not lost').toBe(true);
        instanceBlockState.clear();
        expect(instanceBlock.blocked, 'and it follows the plain state from then on').toBe(false);
    });

    it('one session reset, registered by the plain module, clears both — the face registers none of its own (H’s condition 3)', async () => {
        vi.resetModules();
        const registrations: string[] = [];
        vi.doMock(CLIENT_SESSION, async (importOriginal) => {
            const original = await importOriginal<typeof import('$lib/stores/app/clientSession')>();
            return {
                ...original,
                registerClientSessionReset: (...args: Parameters<typeof original.registerClientSessionReset>) => {
                    registrations.push(args[0]);
                    return original.registerClientSessionReset(...args);
                },
            };
        });

        const instanceBlockState = await importPlainState();
        expect(
            registrations.filter((key) => key === 'instanceBlock'),
            'the plain module, which holds the state, registers its reset when it is imported, once',
        ).toEqual(['instanceBlock']);
        const before = registrations.length;
        const {instanceBlock} = await import('./instanceBlock.svelte');
        expect(registrations.slice(before), 'the reactive face registers no reset of its own: one state, one reset').toEqual([]);

        const {transitionClientSession} = await import('$lib/stores/app/clientSession');
        transitionClientSession(7);
        instanceBlockState.markBlocked();
        expect(instanceBlock.blocked, 'premise: blocked').toBe(true);
        expect(transitionClientSession(8), 'Barrier: another account is a transition').toBe(true);

        expect(instanceBlockState.blocked, 'the change of account clears the plain state').toBe(false);
        expect(instanceBlock.blocked, 'and the face with it').toBe(false);
    });
});
