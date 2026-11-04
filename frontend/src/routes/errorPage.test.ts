// @vitest-environment jsdom
/**
 * The error view, `routes/+error.svelte` — a 404 leaves by itself (workstream H, checkpoint 1, lot FB-23, SPA side).
 *
 * The backend answers any non-API address with the SPA fallback, so an address the router has no route for renders this
 * view with status 404. It used to be a dead end (a card, two links). The contract:
 *   - the card carries `data-testid="error-page"`: the handle the E2E spec `e2e/layout/unknown-address.spec.ts` reads its
 *     absence from (after the page left). Red today: the card has no test id;
 *   - a 404, on mount, leaves the view: with no previous page of the app (a fresh document, as jsdom's is) it is
 *     `goto('/dashboard', {replaceState: true})` — the Dashboard sends a signed-out visitor to the login. (The branch that
 *     goes back to the previous page of the app is the cure's own mechanism and is not pinned here.)
 *   - any other status stays: the same card, no navigation (a 500 is not an address to leave).
 *
 * What is replaced: `$app/stores` (a fixed `page` with the status of the case) and `$app/navigation` (a `goto` spy), and
 * `AnimatedBackground` (a no-op component). `svelte-i18n` is the real one, started by `setupI18n()`: no text is read.
 * `assertEffectsRun` guards the «no navigation» assertion: `onMount` is an effect, and under the wrong environment
 * «goto was not called» would pass vacuously.
 *
 * Written red-first, before the cure.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const mocks = await vi.hoisted(async () => {
    const {writable} = await import('svelte/store');
    return {
        page: writable({status: 404, error: {message: 'Not Found'} as {message: string} | null, url: new URL('http://localhost/this-page-does-not-exist'), params: {}, route: {id: null}, data: {}, form: null, state: {}}),
        goto: vi.fn((..._args: unknown[]) => Promise.resolve()).mockName('goto'),
    };
});

vi.mock('$app/stores', async () => {
    const {readable} = await import('svelte/store');
    return {page: {subscribe: mocks.page.subscribe}, navigating: readable(null), updated: {subscribe: readable(false).subscribe, check: () => Promise.resolve(false)}};
});
vi.mock('$app/navigation', () => ({
    goto: mocks.goto,
    replaceState: vi.fn(),
    pushState: vi.fn(),
    invalidate: vi.fn(() => Promise.resolve()),
    invalidateAll: vi.fn(() => Promise.resolve()),
    preloadCode: vi.fn(() => Promise.resolve()),
    preloadData: vi.fn(() => Promise.resolve()),
    afterNavigate: vi.fn(),
    beforeNavigate: vi.fn(),
    onNavigate: vi.fn(),
}));
vi.mock('$lib/components/ui/AnimatedBackground.svelte', () => ({default: () => {}}));

import {tick} from 'svelte';
import {cleanup, render, screen, setupI18n, waitFor} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import ErrorPage from './+error.svelte';

function showStatus(status: number, message: string): void {
    mocks.page.update((current) => ({...current, status, error: {message}}));
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    assertEffectsRun();
    mocks.goto.mockClear();
});

afterEach(() => {
    cleanup();
});

describe('the error view of an unknown address (FB-23)', () => {
    it('draws its card with the error-page test id, for a 404 and for any other status', () => {
        for (const [status, message] of [
            [404, 'Not Found'],
            [500, 'Internal Error'],
        ] as const) {
            cleanup();
            showStatus(status, message);

            render(ErrorPage);

            expect(screen.queryAllByTestId('error-page'), `status ${status}: one card carries the error-page test id`).toHaveLength(1);
        }
    });

    it('a 404 goes to the Dashboard on mount, replacing its own entry, when there is no previous page of the app', async () => {
        showStatus(404, 'Not Found');
        expect(window.history.length, 'precondition: a fresh jsdom document has no previous page').toBe(1);

        render(ErrorPage);
        await tick();

        await waitFor(() => expect(mocks.goto).toHaveBeenCalledWith('/dashboard', {replaceState: true}));
        expect(mocks.goto).toHaveBeenCalledTimes(1);
    });

    it('any other status stays on its card and navigates nowhere', async () => {
        showStatus(500, 'Internal Error');

        render(ErrorPage);
        await tick();

        // presence barrier: the card is on screen, so the absence of a navigation is about a view that rendered
        expect(screen.queryAllByTestId('error-page'), 'barrier: the 500 card is drawn').toHaveLength(1);
        expect(mocks.goto, 'a 500 does not leave').not.toHaveBeenCalled();
    });
});
