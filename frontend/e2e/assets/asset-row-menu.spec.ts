/**
 * The row menu's disabled item says why, at the touch and from the keyboard (plan 77, SEL-M; Q-SEL-11, Q-SEL-12).
 *
 * An inactive Asset with a provider: «Sync» makes sense for it but is blocked, so the row menu shows it off, with its
 * reason. The item is `aria-disabled` and reachable — a natively disabled button takes no touch and no focus, and a phone
 * shows no `title` — so a tap or the keyboard focus opens the reason in the shared Tooltip. The reason is placed against
 * the whole menu, never over its items, and the menu speaks the WAI-ARIA keyboard: focus on the first item when it opens,
 * arrows through every item (the disabled ones too), Escape back to the ⋮.
 *
 * The list is the test's own: the assets endpoints are mocked (two synthetic Assets), so nothing is written. Read through
 * test ids and data attributes, never through translated text.
 */
import {expect, test} from '../fixtures/playwright';
import type {Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

const INACTIVE_ID = 910_771;
const ACTIVE_ID = 910_772;

function asset(id: number, active: boolean) {
    return {
        id,
        display_name: `Row menu ${active ? 'active' : 'inactive'} ${id}`,
        currency: 'EUR',
        asset_type: 'STOCK',
        active,
        provider_code: 'yfinance',
        tx_count: 0,
        tx_count_own: 0,
        held_by_me: false,
        held_by_others: false,
    };
}

async function openMockedList(page: Page): Promise<void> {
    await page.route('**/api/v1/assets/query*', (route) => route.fulfill({json: [asset(INACTIVE_ID, false), asset(ACTIVE_ID, true)]}));
    await page.route('**/api/v1/assets/prices/query', async (route) => {
        const requested = (route.request().postDataJSON() as Array<{asset_id: number}> | null) ?? [];
        await route.fulfill({json: {items: requested.map(({asset_id}) => ({asset_id, prices: [], events: [], errors: [], signals: []}))}});
    });
    await page.route('**/api/v1/assets/prices/current*', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));
    await navigateTo(page, '/assets');
    await expect(page.getByTestId('assets-page')).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
    // Both lifecycles in view, in the table
    await page.getByTestId('assets-inactive-toggle').click();
    await expect(page.getByTestId('assets-inactive-toggle')).toHaveAttribute('aria-pressed', 'true');
    await page.getByTestId('view-mode-list').click();
    await expect(page.getByTestId(`row-actions-${INACTIVE_ID}`)).toBeVisible({timeout: 10_000});
}

test.describe('The row menu: a disabled item says why (77 SEL-M)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('from the keyboard: the menu takes the focus, the arrows reach the disabled item, its reason opens, Escape goes back to ⋮', async ({page}) => {
        test.skip(test.info().project.name === 'mobile', 'the keyboard case runs on the desktop project; the touch case below sets its own phone');
        await openMockedList(page);
        const trigger = page.getByTestId(`row-actions-${INACTIVE_ID}`);
        await trigger.focus();
        await page.keyboard.press('Enter');
        const menu = page.getByTestId('context-menu');
        await expect(menu).toBeVisible();
        await expect(menu.getByRole('menuitem').first(), 'the menu takes the focus on its first item').toBeFocused();

        const sync = menu.getByTestId('asset-table-sync-action');
        for (let i = 0; i < 10 && !(await sync.evaluate((el) => el === document.activeElement)); i++) await page.keyboard.press('ArrowDown');
        await expect(sync, 'the arrows reach a disabled item').toBeFocused();
        await expect(sync).toHaveAttribute('aria-disabled', 'true');
        await expect(sync).toHaveAttribute('data-disabled-reason', /.+/);
        await expect(page.getByTestId('tooltip-content'), 'its reason opens on the keyboard focus').toBeVisible();

        await page.keyboard.press('Escape');
        await expect(menu).toHaveCount(0);
        await expect(trigger, 'Escape gives the focus back to ⋮').toBeFocused();
    });

    test.describe('on a phone', () => {
        test.use({viewport: {width: 390, height: 844}, hasTouch: true, isMobile: true});

        test('a tap on the disabled item opens its reason above or beside the menu, never over an item; the menu stays open', async ({page}) => {
            await openMockedList(page);
            await page.getByTestId(`row-actions-${INACTIVE_ID}`).tap();
            const menu = page.getByTestId('context-menu');
            await expect(menu).toBeVisible();
            const sync = menu.getByTestId('asset-table-sync-action');
            await expect(sync).toHaveAttribute('aria-disabled', 'true');
            // Playwright reads `aria-disabled` as «not enabled»: the tap is forced, as a finger would land anyway
            await sync.tap({force: true});
            const tip = page.getByTestId('tooltip-content');
            await expect(tip, 'the tap opens the reason').toBeVisible();
            await expect(menu, 'a tap on a disabled item does not close the menu').toBeVisible();

            const clash = await page.evaluate(() => {
                const tipBox = document.querySelector('[data-testid="tooltip-content"]')!.getBoundingClientRect();
                const items = [...document.querySelectorAll('[data-testid="context-menu"] [role="menuitem"]')];
                return items.map((item) => item.getBoundingClientRect()).filter((box) => box.left < tipBox.right - 1 && box.right > tipBox.left + 1 && box.top < tipBox.bottom - 1 && box.bottom > tipBox.top + 1).length;
            });
            expect(clash, 'the reason covers no item of the menu').toBe(0);
        });
    });
});
