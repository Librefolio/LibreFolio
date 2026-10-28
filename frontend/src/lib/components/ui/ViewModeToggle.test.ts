// @vitest-environment jsdom
/**
 * ViewModeToggle — the cards / table switch of the Assets and FX lists (Y2, the FB-8 defect found here too).
 *
 * Each button says what it does in the design system's tooltip (never a `title`, which is a browser tooltip and appears only where
 * the browser decides) and carries a translated accessible name. A click chooses the mode and is the button's own: it stops before
 * the tooltip wrapper's click, which would pin the hint over the list that is redrawn.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import ViewModeToggle from './ViewModeToggle.svelte';

vi.mock('$lib/utils/storage', () => ({getUserStorage: (_key: string, fallback: unknown) => fallback, setUserStorage: vi.fn()}));

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    document.body.innerHTML = '';
});

const RAW_KEY = /^[\w-]+(\.[\w-]+)+$/;

describe('ViewModeToggle', () => {
    it.each(['grid', 'list'] as const)('the %s button sits in a design-system tooltip and carries no title', (mode) => {
        render(ViewModeToggle, {props: {mode: 'grid', storageKey: 'probeViewMode'}});
        const wrapper = screen.getByTestId(`view-mode-${mode}-tooltip`);
        const button = within(wrapper).getByTestId(`view-mode-${mode}`);
        expect(button.hasAttribute('title'), 'a title attribute is a browser tooltip').toBe(false);
        const label = button.getAttribute('aria-label') ?? '';
        expect(label.trim(), 'an accessible name stands in for the text').not.toBe('');
        expect(RAW_KEY.test(label), `the aria-label is a rendered text, not the key "${label}"`).toBe(false);
    });

    it('the two buttons have different names', () => {
        render(ViewModeToggle, {props: {mode: 'grid', storageKey: 'probeViewMode'}});
        expect(screen.getByTestId('view-mode-grid').getAttribute('aria-label')).not.toBe(screen.getByTestId('view-mode-list').getAttribute('aria-label'));
    });

    it('chooses the mode on a click, and the click does not pin the hint over the list', async () => {
        const onchange = vi.fn();
        render(ViewModeToggle, {props: {mode: 'grid', storageKey: 'probeViewMode', onchange}});
        await fireEvent.click(screen.getByTestId('view-mode-list'));
        expect(onchange).toHaveBeenCalledExactlyOnceWith('list');
        // A click on a tooltip's trigger pins its hint; the button's own click must stop before that.
        expect(screen.queryByRole('tooltip'), 'the button owns its click').toBeNull();
    });
});
