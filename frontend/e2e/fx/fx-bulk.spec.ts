/**
 * FX list-view bulk actions & second currency filter — E2E.
 *
 * The list (table) view of the FX page is a large branch the existing fx specs
 * never enter for *selection*: fx-list.spec.ts switches to list only to inspect the
 * column menu. Everything gated behind "a row is selected" — the DataTableToolbar
 * and its four bulk handlers (sync / refresh / invert / delete) — plus the second
 * currency filter and its promote-on-clear logic, were therefore unexercised.
 *
 * Scope is deliberately non-destructive and network-free:
 *   - bulk *sync* only opens the sync modal (no rates are fetched until the user
 *     confirms inside it), so we open it and close it;
 *   - bulk *invert* is an in-memory, per-page-load Map (fxCardInversionStore) that
 *     resets on reload — no DB write, nothing to clean up;
 *   - bulk *delete* is driven through a ConfirmModal; we assert the dialog opens and
 *     then *cancel* it, so no route or rate is ever deleted.
 *
 * What is deliberately NOT covered here, and why: bulk *refresh*, *refresh-all* and
 * the *confirmed* delete all mutate shared FX data (they re-fetch/write rates or
 * delete routes+rates) that other specs read. Under the shared DB + --workers 4 that
 * would be a cross-test write with no clean per-test restore, so they are left to a
 * dedicated destructive spec with disposable pairs. See the report.
 */
import {expect, test} from '../fixtures/playwright';
import type {Locator, Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToFxPage} from './fx-helpers';
import {optionsClosed} from '../fixtures/probe';

const rows = (page: Page) => page.locator('[data-testid="fx-page"] tr[data-row-id]');

async function enterListView(page: Page): Promise<void> {
    await page.getByTestId('view-mode-list').click();
    // The table view is chosen only once its first row has rendered.
    await expect(rows(page).first()).toBeVisible();
}

async function selectAllRows(page: Page): Promise<void> {
    await page.getByTestId('dt-select-all').click();
    await expect(page.getByTestId('selection-toolbar')).toBeVisible();
}

test.describe('FX list-view bulk actions', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToFxPage(page);
        await enterListView(page);
    });

    test('list view renders selectable rows and no toolbar until something is picked', async ({page}) => {
        expect(await rows(page).count()).toBeGreaterThan(0);
        await expect(page.getByTestId('dt-select-all')).toBeVisible();
        await expect(page.getByTestId('selection-toolbar')).toHaveCount(0);
    });

    test('selecting all rows reveals the bulk toolbar with all four actions', async ({page}) => {
        await selectAllRows(page);

        const toolbar = page.getByTestId('selection-toolbar');
        // The count is whatever the page holds — assert it is non-empty, not a literal.
        expect(Number(await toolbar.getAttribute('data-selected-count'))).toBeGreaterThan(0);
        for (const id of ['sync', 'refresh', 'invert', 'delete']) {
            await expect(page.getByTestId(`toolbar-action-${id}`)).toBeVisible();
        }
    });

    test('bulk sync opens the sync modal without fetching rates', async ({page}) => {
        await selectAllRows(page);
        await page.getByTestId('toolbar-action-sync').click();

        await expect(page.getByTestId('fx-sync-modal')).toBeVisible();
        // Close it — nothing is synced until the modal itself is confirmed.
        await page.keyboard.press('Escape');
        await expect(page.getByTestId('fx-sync-modal')).toBeHidden();
    });

    test('bulk invert reverses the pair display and clears the selection', async ({page}) => {
        const firstRow = rows(page).first();
        const slug = await firstRow.getAttribute('data-row-id');
        if (!slug) throw new Error('FX row is missing data-row-id — check FxTable getRowId.');

        // The pair cell is the one carrying the direction arrow "base → quote".
        const pairCell = page.locator(`tr[data-row-id="${slug}"] td`).filter({hasText: '→'});
        const before = (await pairCell.textContent())?.trim() ?? '';
        expect(before.length).toBeGreaterThan(0);

        await selectAllRows(page);
        await page.getByTestId('toolbar-action-invert').click();

        // Selection is cleared (toolbar gone) and the same row now reads reversed.
        await expect(page.getByTestId('selection-toolbar')).toHaveCount(0);
        await expect(pairCell).toContainText('→');
        await expect(pairCell).not.toHaveText(before);
    });

    test('bulk delete opens the confirm dialog; cancelling removes nothing', async ({page}) => {
        const badge = page.getByTestId('fx-pair-count-badge');
        const countBefore = (await badge.textContent())?.trim() ?? '';

        await selectAllRows(page);
        await page.getByTestId('toolbar-action-delete').click();

        // The destructive confirm is shown; we cancel instead of confirming.
        await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible();
        await page.getByTestId('confirm-modal-cancel').click();
        await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0);

        // Selection cleared and every pair still present.
        await expect(page.getByTestId('selection-toolbar')).toHaveCount(0);
        await expect(badge).toHaveText(countBefore);
    });

    test('clearing the selection from the toolbar hides it', async ({page}) => {
        await selectAllRows(page);
        const toolbar = page.getByTestId('selection-toolbar');
        // The count/clear control is the toolbar's first button.
        await toolbar.getByRole('button').first().click();
        await expect(toolbar).toHaveCount(0);
    });
});

test.describe('FX second currency filter', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToFxPage(page);
    });

    // Open a currency filter's dropdown and wait until its option list is actually
    // shown and done loading. SearchSelect focuses an internal search box on open and
    // has a documented 200 ms guard against reopening right after a close, so a single
    // click can be swallowed. Poll the open (only clicking while it is not already
    // expanded, so we never toggle it shut) until the listbox is really there.
    async function openFilterDropdown(page: Page, container: Locator): Promise<Locator> {
        const combo = container.locator('[role="combobox"]');
        const listbox = page.locator('[role="listbox"]');
        await expect(async () => {
            if ((await combo.getAttribute('aria-expanded')) !== 'true') {
                await combo.click();
            }
            await expect(listbox).toBeVisible({timeout: 1_000});
        }).toPass({timeout: 10_000});
        await expect(listbox).toHaveAttribute('aria-busy', 'false', {timeout: 10_000});
        return listbox;
    }

    test('the second filter narrows the pairs and clearing the first promotes the second', async ({page}) => {
        const filters = page.locator('[data-testid="fx-currency-filter"]');
        const filter1 = filters.nth(0);
        const filter2 = filters.nth(1);
        const combo1 = filter1.locator('[role="combobox"]');
        const combo2 = filter2.locator('[role="combobox"]');
        const cards = page.locator('[data-testid^="fx-card-"]');
        const totalBefore = await cards.count();
        expect(totalBefore).toBeGreaterThan(0);

        // Second filter is disabled (tabindex -1) until the first is set.
        await expect(combo2).toHaveAttribute('tabindex', '-1');

        // Filter 1 = EUR (mock data configures EUR-based pairs: USD, GBP, CHF, JPY).
        await openFilterDropdown(page, filter1);
        await page.getByTestId('search-select-option-EUR').first().click();
        await optionsClosed(page);
        const afterEur = await cards.count();
        expect(afterEur).toBeGreaterThan(0);
        expect(afterEur).toBeLessThanOrEqual(totalBefore);

        // Second filter is now enabled; pick USD to pin the EUR/USD pair.
        await expect(combo2).toHaveAttribute('tabindex', '0');
        await openFilterDropdown(page, filter2);
        await page.getByTestId('search-select-option-USD').first().click();
        await optionsClosed(page);
        const afterUsd = await cards.count();
        expect(afterUsd).toBeGreaterThan(0);
        expect(afterUsd).toBeLessThanOrEqual(afterEur);

        // Clear filter 1 via the "All currencies" option (value='' → stable testid,
        // not translated text). The page promotes filter 2 (USD) into filter 1 and
        // clears filter 2.
        await openFilterDropdown(page, filter1);
        await page.getByTestId('search-select-option-').click();
        await optionsClosed(page);

        await expect(combo1).toContainText('USD');
        await expect(combo2).not.toContainText('USD');
    });
});
