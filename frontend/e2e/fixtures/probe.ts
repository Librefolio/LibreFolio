/**
 * Asking whether something showed up, without a sleep in front of the question.
 *
 * `locator.isVisible()` and `locator.count()` answer about *this instant*. They
 * do not retry. So the common shape
 *
 *     await page.waitForTimeout(300);
 *     if (await option.isVisible()) { … }
 *
 * is not "wait for the option": it is "guess how long the option takes, then look
 * once". Guess low and the branch silently goes false — the test skips its own
 * body and still reports green, which is worse than failing.
 *
 * `appears()` asks the same question with a real barrier behind it: it returns as
 * soon as the element is visible, and only spends the full timeout when the
 * element genuinely never arrives. Fast when the answer is yes, honest when no.
 *
 * Use it for branches that are legitimately optional — a control that exists only
 * for some transaction types, a menu that some rows don't have. When the element
 * MUST be there, do not use this: `await expect(x).toBeVisible()` says so, and
 * fails with a useful message when it isn't.
 */

import type {Locator, Page} from '@playwright/test';
import {expect} from './playwright';

/** True as soon as `locator` is visible; false if it never becomes visible in `timeout` ms. */
export async function appears(locator: Locator, timeout = 2_000): Promise<boolean> {
    return locator
        .first()
        .waitFor({state: 'visible', timeout})
        .then(() => true)
        .catch(() => false);
}

/**
 * True as soon as `locator` is enabled; false if it is not enabled within `timeout` ms.
 *
 * `locator.isEnabled({timeout})` waits only for the element to exist, then answers
 * about that instant: a button the page has not enabled yet reads as "never
 * enabled", and the branch behind it is skipped in silence. Same remedy as
 * `appears()`, same rule: when the control MUST become enabled, say so with
 * `await expect(x).toBeEnabled()`.
 */
export async function becomesEnabled(locator: Locator, timeout = 2_000): Promise<boolean> {
    return expect(locator.first())
        .toBeEnabled({timeout})
        .then(
            () => true,
            () => false,
        );
}

/**
 * The SearchSelect option list has closed.
 *
 * Every SearchSelect in the app renders its options as `search-select-option-*`,
 * so while one dropdown is closing its options are indistinguishable from the
 * next dropdown's. A test that opens two selects in a row and clicks `.first()`
 * both times can therefore pick from the WRONG list — which is the real hazard
 * the `waitForTimeout(300)` between them was covering, badly. This says the
 * thing that actually has to be true.
 */
export async function optionsClosed(page: Page): Promise<void> {
    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0);
}
