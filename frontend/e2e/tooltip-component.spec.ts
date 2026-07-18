/**
 * E2E Tests for the shared Tooltip component (Tooltip.svelte).
 *
 * Covers the "pinned" hover/click model fixed in this round: a tooltip
 * opened by plain hover closes promptly on mouse-leave (no timer); a
 * tooltip opened/kept open via click ("pinned") stays open indefinitely
 * while the pointer remains over the trigger OR the tooltip body, and only
 * starts a multi-second grace-dismiss timer once contact actually ends.
 *
 * Bug fixed: previously a fixed 5s auto-dismiss timer fired as soon as a
 * click/tap opened the tooltip, regardless of continued contact — so it
 * could vanish while the user was still trying to read it. Reproduced live
 * via a touch-enabled browser context (a tap made the tooltip disappear at
 * exactly t=5s even with sustained touch contact) before fixing.
 *
 * Uses the "Cost basis override" info tooltip in the ADJUSTMENT transaction
 * form as a real, already-present trigger — no dedicated test page needed.
 */
import {expect, test, type Page} from '@playwright/test';
import {login} from './fixtures/auth-helpers';
import {TEST_USER} from './fixtures/test-users';

async function openAdjustmentCostBasisTooltipTrigger(page: Page) {
    await page.goto('/transactions');
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

    await page.getByTestId('tx-form-type').click();
    await page.getByTestId('search-select-option-ADJUSTMENT').click();

    const brokerWrap = page.getByTestId('tx-form-broker-wrap');
    await brokerWrap.locator("button, [role='combobox']").first().click();
    await page.locator("[data-testid^='search-select-option-']").first().click();

    const assetWrap = page.getByTestId('tx-form-asset-wrap');
    await assetWrap.locator("button, [role='combobox']").first().click();
    await page.locator("[data-testid^='search-select-option-']").first().click();

    await page.getByTestId('tx-form-quantity').fill('5');

    const costBasisWrap = page.getByTestId('tx-form-cost-basis-inline');
    await expect(costBasisWrap).toBeVisible({timeout: 3_000});
    return costBasisWrap.locator('.tooltip-wrapper').first();
}

test.describe('Tooltip component — pinned hover/click model', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('plain hover shows the tooltip and hides it promptly on mouse-leave', async ({page}) => {
        const trigger = await openAdjustmentCostBasisTooltipTrigger(page);
        const box = await trigger.boundingBox();
        expect(box).toBeTruthy();
        if (!box) return;

        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await expect(page.getByTestId('tooltip-content')).toBeVisible({timeout: 1_000});

        await page.mouse.move(10, 10);
        await expect(page.getByTestId('tooltip-content')).not.toBeVisible({timeout: 1_000});
    });

    test('click pins the tooltip open — stays visible well past the old 5s timer while hovered', async ({page}) => {
        test.setTimeout(20_000);
        const trigger = await openAdjustmentCostBasisTooltipTrigger(page);
        await trigger.click();
        await expect(page.getByTestId('tooltip-content')).toBeVisible({timeout: 1_000});

        // The original bug fired a fixed dismiss at t=5s regardless of continued
        // contact — assert it's still visible well past that point.
        await page.waitForTimeout(6_000);
        await expect(page.getByTestId('tooltip-content')).toBeVisible();
    });

    test('after pinning via click, moving the mouse away dismisses after a grace period', async ({page}) => {
        test.setTimeout(20_000);
        const trigger = await openAdjustmentCostBasisTooltipTrigger(page);
        await trigger.click();
        await expect(page.getByTestId('tooltip-content')).toBeVisible({timeout: 1_000});

        await page.mouse.move(10, 10);
        // Still within the grace period — must remain visible.
        await page.waitForTimeout(2_000);
        await expect(page.getByTestId('tooltip-content')).toBeVisible();

        // Grace period elapsed — now it must be gone.
        await expect(page.getByTestId('tooltip-content')).not.toBeVisible({timeout: 6_000});
    });

    test('clicking an already-pinned-open tooltip closes it (explicit toggle-off)', async ({page}) => {
        const trigger = await openAdjustmentCostBasisTooltipTrigger(page);
        await trigger.click();
        await expect(page.getByTestId('tooltip-content')).toBeVisible({timeout: 1_000});

        await trigger.click();
        await expect(page.getByTestId('tooltip-content')).not.toBeVisible({timeout: 1_000});
    });

    test('moving the pointer from the trigger into the tooltip body keeps it open', async ({page}) => {
        const trigger = await openAdjustmentCostBasisTooltipTrigger(page);
        const box = await trigger.boundingBox();
        expect(box).toBeTruthy();
        if (!box) return;

        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        const tooltip = page.getByTestId('tooltip-content');
        await expect(tooltip).toBeVisible({timeout: 1_000});

        const tooltipBox = await tooltip.boundingBox();
        expect(tooltipBox).toBeTruthy();
        if (!tooltipBox) return;
        await page.mouse.move(tooltipBox.x + tooltipBox.width / 2, tooltipBox.y + tooltipBox.height / 2, {steps: 10});

        await page.waitForTimeout(500);
        await expect(tooltip).toBeVisible();
    });

    test('click-outside dismisses a pinned tooltip immediately', async ({page}) => {
        const trigger = await openAdjustmentCostBasisTooltipTrigger(page);
        await trigger.click();
        await expect(page.getByTestId('tooltip-content')).toBeVisible({timeout: 1_000});

        await page.mouse.click(10, 10);
        await expect(page.getByTestId('tooltip-content')).not.toBeVisible({timeout: 1_000});
    });
});
