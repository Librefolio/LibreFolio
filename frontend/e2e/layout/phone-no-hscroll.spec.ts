/**
 * At 375 px no page and no window scrolls sideways (81 U22, developer's note of 23/11/2026).
 *
 * One general control instead of one test per defect: a phone is 375 px wide, and a page or a window that is wider
 * than that is a bug whichever component caused it. Each surface below is its own test, so a red never hides another;
 * the failure names the elements that stick out, outermost first, so the report is the to-do list.
 *
 * The criterion. The page: `documentElement.scrollWidth <= clientWidth` (1 px of rounding). A window: its panel
 * (`.modal-content` of `ModalBase`) is inside the viewport and does not scroll sideways itself. In both, every box
 * that ends past the edge is named, unless it sits inside a container that scrolls or clips on purpose.
 *
 * What is out of the control, declared. A container with `overflow-x: auto | scroll | hidden | clip` is a scroll or
 * clip area by design (the `.table-wrapper` of every DataTable, a chip row, a code block): what is inside it cannot
 * widen the page, so the box that draws it is measured and the content is not. The same goes for anything
 * `position: fixed` (popups, tooltips, the toasts) and for boxes with no size. The rule is the CSS, not a list of
 * names: a list ages, the property does not.
 *
 * Read-only, on the seeded data: nothing is written. The transaction window is opened on a seeded row (its form
 * overflowed on a long asset name before lane 66's TL-1 fix, `tx-form-phone-width.spec.ts` pins that case in
 * detail; here it is one more window of the general sweep).
 *
 * The control has a presence check: a box hung 400 px past the edge must come back by name, or the zeros above mean
 * nothing.
 *
 * The same criterion runs inside the gallery on every shot taken on a phone (`gallery.spec.ts`), collecting the
 * overflows into one report at the end of the run instead of stopping the gallery.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {TEST_USER} from '../fixtures/test-users';
import {measureSidewaysOverflow, OPEN_WINDOW, type SidewaysOverflow} from '../fixtures/phone-overflow';

const PHONE = {width: 375, height: 812};
/** The seeded FX pair and the seeded long-named asset every other specs borrow read-only. */
const SEEDED_FX_PAIR = 'EUR-USD';
const SEEDED_TICKER = 'IWDA';

test.use({viewport: PHONE});

test.beforeEach(async ({page}, testInfo) => {
    // The `mobile` project emulates a 430 px iPhone and a touch screen; this control is about the width alone, so it runs once.
    test.skip(testInfo.project.name !== 'desktop', 'the control sets its own 375 px viewport: one project is enough');
    await page.setViewportSize(PHONE);
    await login(page, TEST_USER);
});

/** The verdict as one assertion whose message is the report: the biggest overflow first, then every outermost box. */
function expectFits(result: SidewaysOverflow, what: string): void {
    const names = result.offenders.map((offender) => `${offender.name} (+${offender.over}px)`).join(' · ');
    expect(result.over, `${what} scrolls sideways at ${result.viewport} px: ${result.over}px past the edge. Outermost boxes: ${names || 'none found (the page itself is wider than its boxes)'}`).toBeLessThanOrEqual(1);
}

/** A seeded id, read through the API the app itself uses. */
async function firstId(page: Page, path: string, pick: (items: any[]) => any): Promise<number> {
    const response = await page.request.get(path);
    expect(response.ok(), `read ${path}: HTTP ${response.status()}`).toBe(true);
    const body = await response.json();
    const item = pick(Array.isArray(body) ? body : (body.items ?? []));
    if (!item) throw new Error(`${path} returned nothing to open: it is seeded by populate_mock_data.py`);
    return item.id as number;
}

test.describe('Pages at 375 px', () => {
    test('the detector sees a box hung past the edge (presence control)', async ({page}) => {
        await navigateTo(page, '/dashboard');
        await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
        await page.evaluate(() => {
            const box = document.createElement('div');
            box.setAttribute('data-testid', 'phone-overflow-probe');
            box.style.cssText = 'position:absolute;top:0;left:0;width:775px;height:4px;';
            document.body.appendChild(box);
        });
        const result = await measureSidewaysOverflow(page);
        expect(result.viewport, 'premise: the page is 375 px wide, so a pass means 375 px').toBe(PHONE.width);
        expect(result.over, 'a 775 px box on a 375 px page went unseen').toBeGreaterThan(300);
        expect(result.offenders.map((offender) => offender.name).join(' '), 'the box was seen but not named').toContain('phone-overflow-probe');
    });

    const PAGES: Array<{name: string; path: () => Promise<string>; ready: string; settle: boolean}> = [
        {name: 'Dashboard', path: async () => '/dashboard', ready: 'dashboard-page', settle: true},
        {name: 'Brokers', path: async () => '/brokers', ready: 'brokers-page', settle: true},
        {name: 'Assets', path: async () => '/assets', ready: 'assets-page', settle: true},
        {name: 'FX', path: async () => '/fx', ready: 'fx-page', settle: true},
        {name: 'Transactions', path: async () => '/transactions', ready: 'transactions-page', settle: true},
        {name: 'Files', path: async () => '/files', ready: 'files-page', settle: true},
        {name: 'Settings', path: async () => '/settings', ready: 'settings-page', settle: false},
    ];
    for (const entry of PAGES) {
        test(`${entry.name} fits the screen`, async ({page}) => {
            await navigateTo(page, await entry.path());
            const root = page.getByTestId(entry.ready);
            await expect(root).toBeVisible({timeout: 20_000});
            if (entry.settle) await waitForSettled(root, 25_000);
            expectFits(await measureSidewaysOverflow(page), entry.name);
        });
    }

    test('a broker page fits the screen', async ({page}) => {
        const id = await firstId(page, '/api/v1/brokers', (items) => items[0]);
        await navigateTo(page, `/brokers/${id}`);
        await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 20_000});
        await waitForSettled(page.getByTestId('broker-detail-page'), 25_000);
        expectFits(await measureSidewaysOverflow(page), `Broker ${id}`);
    });

    test('an asset page fits the screen', async ({page}) => {
        const id = await firstId(page, `/api/v1/assets/query?ticker=${SEEDED_TICKER}`, (items) => items[0]);
        await navigateTo(page, `/assets/${id}`);
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 20_000});
        await waitForSettled(page.getByTestId('asset-detail-page'), 25_000);
        expectFits(await measureSidewaysOverflow(page), `Asset ${SEEDED_TICKER}`);
    });

    test('an FX pair page fits the screen', async ({page}) => {
        await navigateTo(page, `/fx/${SEEDED_FX_PAIR}`);
        await expect(page.getByTestId('fx-detail-page')).toBeVisible({timeout: 20_000});
        await expect(page.getByTestId('fx-detail-page')).toHaveAttribute('data-busy', 'false', {timeout: 25_000});
        expectFits(await measureSidewaysOverflow(page), `FX ${SEEDED_FX_PAIR}`);
    });
});

const WINDOW = OPEN_WINDOW;

test.describe('Windows at 375 px', () => {
    async function expectWindowFits(page: Page, what: string): Promise<void> {
        const panel = page.locator(WINDOW).first();
        await expect(panel, `${what}: the window never opened`).toBeVisible({timeout: 15_000});
        expectFits(await measureSidewaysOverflow(page, WINDOW), what);
    }

    test('the detector sees a box hung past the edge of a window (presence control)', async ({page}) => {
        await navigateTo(page, '/brokers');
        await waitForSettled(page.getByTestId('brokers-page'), 25_000);
        await page.getByTestId('add-broker-button').click();
        await expect(page.locator(WINDOW).first()).toBeVisible({timeout: 15_000});
        await page.evaluate((selector) => {
            const box = document.createElement('div');
            box.setAttribute('data-testid', 'phone-overflow-window-probe');
            box.style.cssText = 'width:600px;height:4px;';
            document.querySelector(selector)?.appendChild(box);
        }, WINDOW);
        const result = await measureSidewaysOverflow(page, WINDOW);
        expect(result.over, 'a 600 px box inside a window on a 375 px page went unseen').toBeGreaterThan(100);
        expect(result.offenders.map((offender) => offender.name).join(' '), 'the box was seen but not named').toContain('phone-overflow-window-probe');
    });

    test('the transaction window, in view mode', async ({page}) => {
        await navigateTo(page, '/transactions');
        await waitForSettled(page.getByTestId('transactions-page'), 25_000);
        const row = page.locator('[data-testid="tx-table"] tbody tr[data-row-id^="tx-"]').first();
        await expect(row, 'the seeded transactions must be on screen').toBeVisible({timeout: 15_000});
        await row.locator('[data-testid^="tx-desc-"]').first().dblclick();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 10_000});
        await expectWindowFits(page, 'Transaction window (view)');
    });

    test('the new-transaction window', async ({page}) => {
        await navigateTo(page, '/transactions');
        await waitForSettled(page.getByTestId('transactions-page'), 25_000);
        await page.getByTestId('tx-add-button').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 10_000});
        await expectWindowFits(page, 'New transaction window');
    });

    test('the import window', async ({page}) => {
        await navigateTo(page, '/transactions');
        await waitForSettled(page.getByTestId('transactions-page'), 25_000);
        await page.getByTestId('tx-import-button').click();
        await expectWindowFits(page, 'Import window');
    });

    test('the «relink events» window', async ({page}) => {
        await navigateTo(page, '/transactions');
        await waitForSettled(page.getByTestId('transactions-page'), 25_000);
        await page.getByTestId('tx-reconcile-events-button').click();
        await expect(page.getByTestId('event-reconciliation-modal')).toBeVisible({timeout: 10_000});
        await expectWindowFits(page, 'Relink events window');
    });

    test('the new-asset window', async ({page}) => {
        await navigateTo(page, '/assets');
        await waitForSettled(page.getByTestId('assets-page'), 25_000);
        await page.getByTestId('assets-add-button').click();
        await expectWindowFits(page, 'New asset window');
    });

    test('the new-broker window', async ({page}) => {
        await navigateTo(page, '/brokers');
        await waitForSettled(page.getByTestId('brokers-page'), 25_000);
        await page.getByTestId('add-broker-button').click();
        await expectWindowFits(page, 'New broker window');
    });

    test('the add-FX-pair window', async ({page}) => {
        await navigateTo(page, '/fx');
        await waitForSettled(page.getByTestId('fx-page'), 25_000);
        await page.getByTestId('fx-add-pair-button').click();
        await expect(page.getByTestId('fx-add-pair-modal')).toBeVisible({timeout: 10_000});
        await expectWindowFits(page, 'Add FX pair window');
    });
});
