/**
 * authFlash — the one message a link page hands to the login page (accounts lot A5b).
 *
 * The two link pages end on the login page: `/invite` after an account was created, `/reset-password` after a password
 * was changed. The login page is another route, so the message cannot travel as a prop: the link page calls
 * `setAuthFlash(message)` just before `goto('/')`, and the login page starts its success message from
 * `takeAuthFlash()`.
 *
 * The contract (plan A5b.1):
 *   - `takeAuthFlash()` returns the message that was set, once, and clears it: a second take, a reload of the login
 *     page or a later visit finds `''`;
 *   - `''` when nothing was set;
 *   - one slot: a message set after another replaces it.
 *
 * The flash is module state, so every case takes a freshly imported module (`vi.resetModules()` + `import()`): no case
 * inherits a neighbour's message, in any order, and "before anything was set" is the state of a page load that has
 * just begun, not the state after a drain.
 *
 * Written red-first, before `authFlash.ts` exists: every case fails on the import until it does.
 */
import {describe, expect, it, vi} from 'vitest';

/** The module of a page load that has just begun. */
async function freshPageLoad(): Promise<typeof import('./authFlash')> {
    vi.resetModules();
    return import('./authFlash');
}

describe('authFlash — a message handed over once', () => {
    it('has nothing to say on a page load where nothing was set', async () => {
        const {takeAuthFlash} = await freshPageLoad();

        expect(takeAuthFlash()).toBe('');
    });

    it('hands back the message that was set', async () => {
        const {setAuthFlash, takeAuthFlash} = await freshPageLoad();

        setAuthFlash('a message the link page left');

        expect(takeAuthFlash()).toBe('a message the link page left');
    });

    it('hands it back only once: the next take finds nothing', async () => {
        const {setAuthFlash, takeAuthFlash} = await freshPageLoad();
        setAuthFlash('once');

        expect(takeAuthFlash(), 'premise: the first take gets it').toBe('once');
        expect(takeAuthFlash(), 'a second take, as a remounted login page would make, gets nothing').toBe('');
    });

    it('keeps one message: the latest one set replaces the one before', async () => {
        const {setAuthFlash, takeAuthFlash} = await freshPageLoad();

        setAuthFlash('first');
        setAuthFlash('second');

        expect(takeAuthFlash()).toBe('second');
        expect(takeAuthFlash(), 'and the replaced message does not come back afterwards').toBe('');
    });

    it('can be set again after a take', async () => {
        const {setAuthFlash, takeAuthFlash} = await freshPageLoad();
        setAuthFlash('first visit');
        takeAuthFlash();

        setAuthFlash('second visit');

        expect(takeAuthFlash()).toBe('second visit');
    });
});

/**
 * The tone of the message (lot E-26 (b), developer decision of 23/10/2026): a registration whose activation email was
 * held leaves a warning, not a success. `setAuthFlash(message, tone?)` takes the tone, `'success'` when omitted;
 * `takeAuthFlashTone()` returns it once and clears it, so a later message without a tone is a success again.
 */
describe('authFlash — the tone of the message', () => {
    it('is a success when none was given, and when nothing was set', async () => {
        const {setAuthFlash, takeAuthFlashTone} = await freshPageLoad();

        expect(takeAuthFlashTone(), 'nothing set').toBe('success');

        setAuthFlash('a message');

        expect(takeAuthFlashTone(), 'no tone given').toBe('success');
    });

    it('hands back the tone that was set, once', async () => {
        const {setAuthFlash, takeAuthFlashTone} = await freshPageLoad();
        setAuthFlash('held', 'warning');

        expect(takeAuthFlashTone(), 'premise: the tone that was set').toBe('warning');
        expect(takeAuthFlashTone(), 'a second take finds the default').toBe('success');
    });

    it('is replaced with the message: a later message without a tone is a success', async () => {
        const {setAuthFlash, takeAuthFlashTone} = await freshPageLoad();

        setAuthFlash('held', 'warning');
        setAuthFlash('created');

        expect(takeAuthFlashTone()).toBe('success');
    });

    it('does not disturb the message: taking the tone first, or last, leaves the message to takeAuthFlash', async () => {
        const {setAuthFlash, takeAuthFlash, takeAuthFlashTone} = await freshPageLoad();
        setAuthFlash('held', 'warning');

        expect(takeAuthFlashTone()).toBe('warning');
        expect(takeAuthFlash()).toBe('held');
    });
});
