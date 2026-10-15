/**
 * Reaching a header control by keyboard, so that it pins the header (the rule of step T-7, colour workstream T).
 *
 * The app header hides on a downward scroll. Keyboard focus inside it pins it — a keyboard user must not lose the
 * control they are on — while the focus a mouse click leaves on a header button (Chrome keeps it there) does not, so
 * that after a click on, say, the theme toggle the header still hides on scroll. Header.svelte draws the line with
 * `:focus-visible`, in `focusPinsHeader()`: the pin is set on `focusin` and checked again on `focusout`.
 *
 * A scripted `focus()` does not pick a side: Chrome matches `:focus-visible` on it only when the page's last interaction
 * was the keyboard. After a click anywhere on the page it does not, and the header stays free to hide — a spec that
 * focuses a header control to keep the header on screen would read `visible` where it expects `pinned`. A focus that
 * arrives by a key press is `:focus-visible` whatever came before. So the control is focused, left with Tab and reached
 * again with Shift+Tab: the last hop is the keyboard's.
 *
 * Tab lands on the next control of the header — `theme-toggle` after `privacy-toggle`, on both projects; the coffee
 * link after `mobile-menu-toggle`, the burger of the mobile project — which pins the header as well; Shift+Tab comes
 * back. The helper proves the control focused and `:focus-visible`. That the header is pinned stays the caller's own
 * assertion.
 */
import {expect, type Page} from './playwright';

/** Focus the header control with this test id by keyboard: focus(), Tab to the next control, Shift+Tab back. */
export async function focusHeaderControlByKeyboard(page: Page, testId: string): Promise<void> {
    const control = page.getByTestId('app-header').getByTestId(testId);
    await control.focus();
    await page.keyboard.press('Tab');
    await expect(control, `Tab moves the focus from ${testId} to the next control of the header`).not.toBeFocused();
    await page.keyboard.press('Shift+Tab');
    await expect(control, `Shift+Tab brings the focus back to ${testId}`).toBeFocused();
    expect(await control.evaluate((element) => element.matches(':focus-visible')), `${testId} is reached by keyboard: it matches :focus-visible`).toBe(true);
}
