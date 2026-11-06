/**
 * The ← of the main pages (Brokers, Transactions, Assets, FX), drawn only after an in-app link (testlist B-6).
 *
 * The detail pages have always had a ← and the main pages did not, so a «see all» link broke the rhythm: no way back
 * but the browser's button, which the installed desktop app lacks. The main pages now draw the same ← — but only while
 * the app's own back stack holds a page below the current one (`navigationStore.canGoBack`). Entered from the sidebar
 * or by typing the address, a ← would lead nowhere, so it is not there.
 *
 *   with     Brokers (typed address) → a broker → «view in Transactions»: the Transactions page has its ←, and pressing it
 *            returns to that broker as it was left, on the period chosen there (the toolbar's preset stays active).
 *   without  a typed address, on each of the four pages; the sidebar from the same deep page (the stack is reset); and a
 *            ← that returned to the section root, which has nothing below it any more.
 *
 * Read-only: the shared user and a seeded broker are only navigated; nothing is written. Waiting is on the pages' own
 * `data-busy` and on the test ids the app publishes, with deadlines; an absence is read only after the page it is
 * absent from has landed. No translated text is read.
 *
 * Key data-testids:
 *   nav-brokers|transactions|assets|fx, brokers-page|transactions-page|assets-page|fx-page [data-busy]
 *   brokers-back-btn|transactions-back-btn|assets-back-btn|fx-back-btn, broker-card-{id}, broker-detail-page
 *   broker-back-button, broker-view-in-transactions, date-preset-1m [data-active]
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login, openMobileMenu} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {TEST_USER} from '../fixtures/test-users';

const LOAD_TIMEOUT = 20_000;
const UI_TIMEOUT = 10_000;

const MAIN_PAGES = [
    {page: 'brokers', nav: 'nav-brokers', arrow: 'brokers-back-btn', route: '/brokers'},
    {page: 'transactions', nav: 'nav-transactions', arrow: 'transactions-back-btn', route: '/transactions'},
    {page: 'assets', nav: 'nav-assets', arrow: 'assets-back-btn', route: '/assets'},
    {page: 'fx', nav: 'nav-fx', arrow: 'fx-back-btn', route: '/fx'},
] as const;

/** Where a sidebar item goes: the burger first on a phone. */
async function viaSidebar(page: Page, navTestId: string): Promise<void> {
    await openMobileMenu(page);
    await page.getByTestId(navTestId).click();
}

/** Path and query of the page on view. */
async function currentAddress(page: Page): Promise<string> {
    const {pathname, search} = new URL(page.url());
    return pathname + search;
}

/** The page has landed (its own data-busy), so an absence on it is an absence and not a page not yet drawn. */
async function landed(page: Page, pageTestId: string): Promise<void> {
    await expect(page.getByTestId(`${pageTestId}-page`)).toBeVisible({timeout: LOAD_TIMEOUT});
    await waitForSettled(page, LOAD_TIMEOUT);
}

test.describe('Main pages draw a ← only after an in-app link (B-6)', () => {
    test.setTimeout(90_000);

    test('Brokers → a broker → «view in Transactions»: the ← returns to the broker, with its period', async ({page}) => {
        await login(page, TEST_USER);
        await page.goto('/brokers');
        await landed(page, 'brokers');
        // A typed address: nothing below the page, so no ←.
        await expect(page.getByTestId('brokers-back-btn')).toHaveCount(0);

        // Which broker is irrelevant: whichever is clicked is the one the ← must return to, by its id.
        const card = page.locator('[data-testid^="broker-card-"]').first();
        const cardTestId = await card.getAttribute('data-testid');
        const brokerId = cardTestId?.replace('broker-card-', '');
        expect(brokerId, 'a broker card on the list').toBeTruthy();
        await card.click();
        await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: LOAD_TIMEOUT});
        await expect.poll(() => new URL(page.url()).pathname, {timeout: UI_TIMEOUT}).toBe(`/brokers/${brokerId}`);

        // A period chosen on the broker, which the ← must find again.
        await page.getByTestId('date-preset-1m').click();
        await expect(page.getByTestId('date-preset-1m')).toHaveAttribute('data-active', 'true', {timeout: UI_TIMEOUT});
        await waitForSettled(page, LOAD_TIMEOUT);

        // The link sits in the commands row of the Transactions tab.
        await page.getByTestId('broker-tab-transazioni').click();
        await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: UI_TIMEOUT});
        const toTransactions = page.getByTestId('broker-transactions-actions').getByTestId('broker-view-in-transactions');
        await expect(toTransactions).toBeVisible({timeout: LOAD_TIMEOUT});
        const leftAt = await currentAddress(page); // the tab is part of where the broker was left
        await toTransactions.click();
        await expect.poll(() => new URL(page.url()).pathname, {timeout: LOAD_TIMEOUT}).toBe('/transactions');
        await landed(page, 'transactions');
        const arrow = page.getByTestId('transactions-back-btn');
        await expect(arrow).toBeVisible({timeout: UI_TIMEOUT});

        await arrow.click();
        await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: LOAD_TIMEOUT});
        await expect.poll(() => currentAddress(page), {timeout: UI_TIMEOUT, message: 'the broker comes back at the address it was left at'}).toBe(leftAt);
        await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: UI_TIMEOUT});
        await expect(page.getByTestId('date-preset-1m')).toHaveAttribute('data-active', 'true', {timeout: UI_TIMEOUT});
    });

    for (const target of MAIN_PAGES) {
        test(`${target.page}: no ← on a typed address`, async ({page}) => {
            await login(page, TEST_USER);
            await page.goto(target.route);
            await landed(page, target.page);
            await expect(page.getByTestId(target.arrow)).toHaveCount(0);
        });
    }

    test('no ← on the four pages when reached from the sidebar, even from deep inside the app', async ({page}) => {
        await login(page, TEST_USER);
        await page.goto('/brokers');
        await landed(page, 'brokers');
        const card = page.locator('[data-testid^="broker-card-"]').first();
        await card.click();
        await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: LOAD_TIMEOUT});

        // The sidebar clears the stack: the section it opens is a root, whatever was behind it.
        for (const target of MAIN_PAGES) {
            await viaSidebar(page, target.nav);
            await expect.poll(() => new URL(page.url()).pathname, {timeout: LOAD_TIMEOUT}).toBe(target.route);
            await landed(page, target.page);
            await expect(page.getByTestId(target.arrow), `${target.page} entered from the sidebar`).toHaveCount(0);
        }
    });

    test('no ← once ← itself has returned to the section root', async ({page}) => {
        await login(page, TEST_USER);
        await page.goto('/brokers');
        await landed(page, 'brokers');
        await page.locator('[data-testid^="broker-card-"]').first().click();
        await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: LOAD_TIMEOUT});

        await page.getByTestId('broker-back-button').click();
        await landed(page, 'brokers');
        await expect(page.getByTestId('brokers-back-btn')).toHaveCount(0);
    });
});
