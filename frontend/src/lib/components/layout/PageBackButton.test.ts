// @vitest-environment jsdom
/**
 * PageBackButton — the ← of the four main pages (B-6), mounted over the real navigationStore.
 *
 * The contract: it exists only while a page is stacked below the current one, it follows the stack as the user
 * navigates (the button is in the DOM before afterNavigate tracks the page, so it must appear afterwards), and
 * pressing it goes back through `goBack`, to the page as it was left.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';

const {goto} = vi.hoisted(() => ({goto: vi.fn()}));
vi.mock('$app/navigation', () => ({goto}));

import PageBackButton from './PageBackButton.svelte';
import {resetNavDepth, trackNavigation} from '$lib/stores/app/navigationStore';

const BUTTON = 'assets-back-btn';

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    cleanup();
    goto.mockReset();
    resetNavDepth();
});

describe('PageBackButton', () => {
    it('is absent on a direct address', () => {
        trackNavigation('enter', '/assets');
        render(PageBackButton, {fallback: '/dashboard', testId: BUTTON});
        expect(screen.queryByTestId(BUTTON)).toBeNull();
    });

    it('is absent after a sidebar click (the stack was reset)', () => {
        trackNavigation('enter', '/dashboard');
        resetNavDepth();
        trackNavigation('link', '/assets');
        render(PageBackButton, {fallback: '/dashboard', testId: BUTTON});
        expect(screen.queryByTestId(BUTTON)).toBeNull();
    });

    it('is present after an in-app link', () => {
        trackNavigation('enter', '/dashboard');
        trackNavigation('link', '/assets');
        render(PageBackButton, {fallback: '/dashboard', testId: BUTTON});
        expect(screen.getByTestId(BUTTON)).toBeTruthy();
    });

    it('appears when the navigation is tracked after the page was mounted, and goes when the section is reset', () => {
        trackNavigation('enter', '/dashboard');
        render(PageBackButton, {fallback: '/dashboard', testId: BUTTON});
        expect(screen.queryByTestId(BUTTON)).toBeNull();
        trackNavigation('link', '/assets'); // afterNavigate runs once the new page is in the DOM
        flushSync();
        expect(screen.getByTestId(BUTTON)).toBeTruthy();
        resetNavDepth();
        flushSync();
        expect(screen.queryByTestId(BUTTON)).toBeNull();
    });

    it('goes back to the page it came from, with its period and filters', async () => {
        trackNavigation('enter', '/dashboard?start=2026-01-01&end=2026-06-30');
        trackNavigation('link', '/assets?start=2026-02-01');
        render(PageBackButton, {fallback: '/fallback-never-tracked', testId: BUTTON});
        await fireEvent.click(screen.getByTestId(BUTTON));
        expect(goto).toHaveBeenCalledTimes(1);
        expect(goto).toHaveBeenCalledWith('/dashboard?start=2026-01-01&end=2026-06-30');
    });

    // BTN-2a: the standard Button names an icon by its aria-label and shows the name on a rest or a long press; a native
    // `title` would be a second, browser-drawn tooltip of the same text.
    it('is named after the generic «back» label for assistive tools, with no native title', () => {
        trackNavigation('enter', '/dashboard');
        trackNavigation('link', '/assets');
        render(PageBackButton, {fallback: '/dashboard', testId: BUTTON});
        const button = screen.getByTestId(BUTTON);
        expect(button.getAttribute('aria-label')).toBeTruthy();
        expect(button.getAttribute('aria-label')).not.toBe('common.back'); // the key resolved, not shown raw
        expect(button.hasAttribute('title'), 'the name is the tooltip of the standard button, not a title').toBe(false);
    });
});
