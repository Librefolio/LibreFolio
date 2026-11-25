// @vitest-environment jsdom
/**
 * CheckMenu — the clear of a filter menu is the standard Button (85 BTN-2c).
 *
 * It exists only while a value is on; it is a text link (`variant="link"`) named by its word (the caller's
 * `clearLabel`), never a toggle, so the options stay the only `[aria-pressed]` under the menu's prefix; a click calls
 * `onclear`. The options are hand-written rows with `aria-pressed`, as before.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {Filter} from 'lucide-svelte';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import CheckMenu from './CheckMenu.svelte';

const TID = 'probe-menu';
const ITEMS = [
    {value: 'STOCK', label: 'Stocks', count: 3},
    {value: 'ETF', label: 'Funds', count: 2},
];

beforeAll(async () => {
    await setupI18n();
});

function mount(selected: string[]) {
    const ontoggle = vi.fn();
    const onclear = vi.fn();
    render(CheckMenu, {props: {label: 'Type', icon: Filter, items: ITEMS, selected, ontoggle, onclear, clearLabel: 'probe: clear the type', testId: TID}});
    return {ontoggle, onclear};
}

async function open(): Promise<HTMLElement> {
    await fireEvent.click(screen.getByTestId(`${TID}-button`));
    return screen.getByTestId(`${TID}-panel`);
}

describe('CheckMenu — the clear (85 BTN-2c)', () => {
    it('no value on: no clear', async () => {
        mount([]);
        const panel = await open();
        expect(within(panel).getByTestId(`${TID}-STOCK`), 'barrier: the panel is open').toBeInTheDocument();
        expect(within(panel).queryByTestId(`${TID}-clear`)).toBeNull();
    });

    it('a value on: the clear is a Button named by its word, never a toggle, and clears', async () => {
        const {onclear, ontoggle} = mount(['ETF']);
        const panel = await open();
        const clear = within(panel).getByTestId(`${TID}-clear`);
        expect(clear.tagName).toBe('BUTTON');
        expect(clear.textContent?.trim()).toBe('probe: clear the type');
        expect(clear.hasAttribute('aria-pressed'), 'the options stay the only toggles').toBe(false);
        expect([...panel.querySelectorAll('[aria-pressed]')].map((el) => el.getAttribute('data-testid'))).toEqual([`${TID}-STOCK`, `${TID}-ETF`]);
        await fireEvent.click(clear);
        expect(onclear).toHaveBeenCalledTimes(1);
        expect(ontoggle).not.toHaveBeenCalled();
    });
});
