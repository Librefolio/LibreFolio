/**
 * An address the web app does not know leads to the app (workstream H, checkpoint 1, lot FB-23, SPA side).
 *
 * Contract. The backend serves the SPA fallback for any path that is not `api/…` or `mkdocs…`, so a mistyped or stale
 * address (`/this-page-does-not-exist-…`) reaches the SvelteKit router, which finds no route and renders
 * `src/routes/+error.svelte` with status 404. That view used to be a dead end: a card with two links. The cure makes a
 * 404 leave by itself, on mount: it goes back to the previous page of the app when there is one, otherwise
 * `goto('/dashboard', {replaceState: true})`; the Dashboard (an `(app)` page) sends a signed-out visitor to the login.
 * So, from a fresh navigation to an unknown address (no previous page of the app):
 *
 *   1. signed in: the page ends on `/dashboard`, in the app shell, and the 404 view is no longer on screen;
 *   2. signed out: the page ends on the login (`login-page`, at `/`), and the 404 view is no longer on screen.
 *
 * "The 404 view is no longer on screen" is `[data-testid="error-page"]` having nothing to show. The error card carries
 * that test id (the cure adds `data-testid="error-page"` to the card in `+error.svelte`; before it the id is simply
 * absent, so the absence below would pass on a page that never left). An absence is therefore only read after a
 * presence barrier — the app shell or the login is visible, so the page did arrive somewhere else — and the id itself is
 * pinned present on a 404 render by the component test `src/routes/errorPage.test.ts`. The URL assertions are the ones
 * that are red today: a 404 stays on the address that was typed.
 *
 * Not here: the «previous page of the app» branch (a link inside the app to an address that does not exist; there is
 * no such link to click, and the unit test of the view covers the choice).
 *
 * Read-only: the signed-in case only signs in as the shared user; nothing is written. Waiting is on the URL and on the
 * test ids the app publishes, with deadlines, never on the clock; no translated text is read.
 */
import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {uniqueSuffix} from '../fixtures/unique';
import {TEST_USER} from '../fixtures/test-users';

/** From the document load to the 404 view's own redirect and the arrival page: client-side hops on a loaded machine. */
const ARRIVAL_MS = 20_000;

/** An address no route holds, different in every call. */
function unknownAddress(): string {
    return `/this-page-does-not-exist-${uniqueSuffix()}`;
}

test.describe('An unknown address leads to the app (FB-23)', () => {
    test('signed in, an unknown address ends on the Dashboard and not on the 404 view', async ({page}) => {
        await login(page, TEST_USER);
        const address = unknownAddress();

        await page.goto(address);

        await expect.poll(() => new URL(page.url()).pathname, {message: `the unknown address ${address} leaves for /dashboard`, timeout: ARRIVAL_MS}).toBe('/dashboard');
        // presence barrier: the page arrived in the app, so the absence below is about a view that left, not one that never rendered
        await expect(page.getByTestId('app-shell')).toBeVisible({timeout: ARRIVAL_MS});
        await expect(page.getByTestId('error-page')).toHaveCount(0);
    });

    test('signed out, an unknown address ends on the login and not on the 404 view', async ({page}) => {
        await page.context().clearCookies();
        const address = unknownAddress();

        await page.goto(address);

        await expect(page.getByTestId('login-page')).toBeVisible({timeout: ARRIVAL_MS});
        expect(new URL(page.url()).pathname, 'the login is at the root, not at the unknown address').toBe('/');
        await expect(page.getByTestId('error-page')).toHaveCount(0);
    });
});
