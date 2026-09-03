/**
 * E2E Tests for the shared Tooltip component (Tooltip.svelte).
 *
 * Covers the "pinned" hover/click model fixed in this round: a tooltip
 * opened by plain hover closes promptly on mouse-leave (no timer); a
 * tooltip opened/kept open via click ("pinned") stays open indefinitely
 * while the pointer remains over the trigger OR the tooltip body, and only
 * starts a 30-second grace-dismiss timer once contact actually ends.
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
import {expect, test, type Page} from './fixtures/playwright';
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
        // T2: a plain hover opens only after the 500ms rest delay, so the
        // auto-wait must have room for the delay itself, not just for rendering.
        await expect(page.getByTestId('tooltip-content')).toBeVisible({timeout: 2_500});

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

    test('after pinning via click, moving the mouse away dismisses after 30 seconds', async ({page}) => {
        test.setTimeout(20_000);
        const trigger = await openAdjustmentCostBasisTooltipTrigger(page);
        await trigger.click();
        await expect(page.getByTestId('tooltip-content')).toBeVisible({timeout: 1_000});

        await page.clock.install();
        await page.mouse.move(10, 10);
        await page.clock.fastForward(29_000);
        await expect(page.getByTestId('tooltip-content')).toBeVisible();

        await page.clock.fastForward(1_100);
        await expect(page.getByTestId('tooltip-content')).not.toBeVisible({timeout: 1_000});
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
        // T2: the open lands only after the 500ms hover delay — see the first test.
        await expect(tooltip).toBeVisible({timeout: 2_500});

        const tooltipBox = await tooltip.boundingBox();
        expect(tooltipBox).toBeTruthy();
        if (!tooltipBox) return;
        await page.mouse.move(tooltipBox.x + tooltipBox.width / 2, tooltipBox.y + tooltipBox.height / 2, {steps: 10});

        await expect(tooltip).toBeVisible();
    });

    test('click-outside dismisses a pinned tooltip immediately', async ({page}) => {
        const trigger = await openAdjustmentCostBasisTooltipTrigger(page);
        await trigger.click();
        const tooltip = page.getByTestId('tooltip-content');
        await expect(tooltip).toBeVisible({timeout: 1_000});

        // Being *visible* is not the same as being *dismissable*: the outside-click
        // listener is attached by an `$effect`, which runs after the element is in
        // the DOM. Clicking inside that window hits nobody, and a missed dismissal
        // does not just arrive late — the tooltip stays pinned for its 30-second
        // grace period, so the assertion below could never pass. That is what made
        // this test fail about one run in four under load; a longer timeout would
        // have hidden it rather than fixed it.
        await expect(tooltip).toHaveAttribute('data-dismissable', 'true', {timeout: 2_000});

        await page.mouse.click(10, 10);
        // Retrying assertion: it returns as soon as the tooltip is gone, so the
        // generous ceiling costs nothing when things are fast.
        await expect(tooltip).not.toBeVisible({timeout: 5_000});
    });
});

/**
 * T2 — the hover-open delay itself (default `showDelayMs` = 500).
 *
 * These run on the page's *mocked* clock (`page.clock.install()`): the delay
 * is a `setTimeout` in the component, so advancing the clock is the honest way
 * to let "300ms of hovering" pass without a real sleep. Two disciplines fall
 * out of the mocked clock and are load-bearing:
 *
 *   - only `page.mouse.*` / `page.keyboard.*` after the install: `locator.click()`
 *     actionability waits on requestAnimationFrame, which the fake clock holds
 *     until a fastForward — a real click would hang;
 *   - every assertion is already true when it runs. Playwright's first check is
 *     immediate, but a *retry* polls on the (faked) rAF and would never re-run.
 */
test.describe('Tooltip component — hover-open delay (T2)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('hover under the delay does not open; crossing it does', async ({page}) => {
        const trigger = await openAdjustmentCostBasisTooltipTrigger(page);
        const box = await trigger.boundingBox();
        expect(box).toBeTruthy();
        if (!box) return;

        await page.clock.install();

        // Rest the pointer on the trigger for 300ms < 500ms: nothing opens.
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await page.clock.fastForward(300);
        await expect(page.getByTestId('tooltip-content')).toHaveCount(0);

        // Crossing the delay fires the pending open.
        await page.clock.fastForward(250);
        await expect(page.getByTestId('tooltip-content')).toBeVisible();
    });

    test('leaving before the delay elapses cancels the pending open', async ({page}) => {
        const trigger = await openAdjustmentCostBasisTooltipTrigger(page);
        const box = await trigger.boundingBox();
        expect(box).toBeTruthy();
        if (!box) return;

        await page.clock.install();

        // Hover 300ms, leave, then run the clock well past the delay: the timer
        // must have been cancelled, not merely postponed.
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await page.clock.fastForward(300);
        await page.mouse.move(10, 10);
        await page.clock.fastForward(1_000);
        await expect(page.getByTestId('tooltip-content')).toHaveCount(0);
    });

    test('click and keyboard open instantly, inside the hover-delay window', async ({page}) => {
        const trigger = await openAdjustmentCostBasisTooltipTrigger(page);
        const box = await trigger.boundingBox();
        expect(box).toBeTruthy();
        if (!box) return;

        await page.clock.install();

        // mouse.click moves the pointer onto the trigger first — the hover branch
        // starts its 500ms timer — then clicks. The clock is never forwarded, so
        // that timer can never fire: if the tooltip is visible now, the explicit
        // path opened it.
        await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
        await expect(page.getByTestId('tooltip-content')).toBeVisible();

        // Toggle off, then the keyboard path (Enter on the focused trigger).
        await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
        await expect(page.getByTestId('tooltip-content')).toHaveCount(0);
        await trigger.focus();
        await page.keyboard.press('Enter');
        await expect(page.getByTestId('tooltip-content')).toBeVisible();
    });
});
